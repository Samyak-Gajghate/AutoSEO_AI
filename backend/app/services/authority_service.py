import json
import math
from typing import List
from google.cloud import firestore
from app.rag.embedder import embed_texts
from app.llm.service import llm_service

_db = None


def get_db():
    global _db
    if _db is None:
        _db = firestore.AsyncClient()
    return _db


def _kmeans_cluster(vectors: List[List[float]], k: int, max_iter: int = 50):
    """
    Simple K-means implementation using numpy for clustering keyword embeddings.
    Returns cluster assignment list of length n.
    """
    import numpy as np
    X = np.array(vectors)
    # Random initialization
    indices = np.random.choice(len(X), k, replace=False)
    centroids = X[indices]

    labels = [0] * len(X)
    for _ in range(max_iter):
        # Assignment step
        new_labels = []
        for v in X:
            dists = [np.linalg.norm(v - c) for c in centroids]
            new_labels.append(int(np.argmin(dists)))

        if new_labels == labels:
            break
        labels = new_labels

        # Update step
        for i in range(k):
            cluster_pts = X[[j for j, l in enumerate(labels) if l == i]]
            if len(cluster_pts) > 0:
                centroids[i] = cluster_pts.mean(axis=0)

    return labels


async def compute_authority_score(uid: str) -> List[dict]:
    """
    1. Fetches all project keywords for a user
    2. Embeds them
    3. K-means clusters (k = max(2, sqrt(n)))
    4. LLM labels each cluster + suggests expansion articles
    Returns list of AuthorityCluster dicts.
    """
    db = get_db()

    # Fetch all user projects
    docs = db.collection("projects").where("user_id", "==", uid).stream()
    projects = []
    async for doc in docs:
        d = doc.to_dict()
        projects.append({"id": doc.id, "keyword": d.get("keyword", "")})

    if len(projects) < 2:
        return []

    keywords = [p["keyword"] for p in projects]
    vectors = await embed_texts(keywords)

    # Dynamic K
    k = max(2, int(math.isqrt(len(keywords))))
    labels = _kmeans_cluster(vectors, k)

    # Group keywords by cluster
    clusters: dict[int, List[str]] = {}
    for kw, label in zip(keywords, labels):
        clusters.setdefault(label, []).append(kw)

    # Ask LLM to label clusters and suggest expansion
    cluster_text = json.dumps([
        {"cluster_id": i, "keywords": kws}
        for i, kws in clusters.items()
    ])
    raw_suggestions = await llm_service.suggest_improvements(
        uid=uid,
        keyword="topical authority analysis",
        article=cluster_text,
        competitor_context=(
            "These are keyword clusters from the user's content library. "
            "Label each cluster and suggest 1-3 additional articles that would strengthen authority."
        ),
    )

    # Build result
    result = []
    for i, kws in clusters.items():
        # coverage score: ratio of cluster size vs ideal cluster depth (target: 5 articles)
        score = min(len(kws) / 5.0, 1.0)
        suggestions = []
        if isinstance(raw_suggestions, dict):
            for cluster_info in raw_suggestions.get("clusters", []):
                suggestions = cluster_info.get("suggestions", [])[:3]
                break  # simplified mapping

        result.append({
            "label": f"Cluster {i + 1}",
            "keywords": kws,
            "score": round(score, 2),
            "suggestions": suggestions,
        })

    return result
