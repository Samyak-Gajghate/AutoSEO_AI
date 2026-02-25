import re
from typing import Tuple


def compute_rule_score(
    content: str,
    keyword: str,
    meta_title: str = "",
    meta_description: str = "",
) -> Tuple[int, list[str]]:
    """
    Rule-based SEO scoring. Returns (score 0–100, list of feedback strings).

    Scoring breakdown:
      - Keyword density       : 0–25 pts
      - Heading distribution  : 0–20 pts
      - Word count            : 0–20 pts
      - Keyword in first 100w : 0–20 pts
      - Meta optimization     : 0–15 pts
    """
    feedback = []
    total = 0
    words = content.split()
    word_count = len(words)
    kw = keyword.lower()

    # ── 1. Keyword density (target: 0.5% – 2.0%) ──────────────────────────
    occurrences = content.lower().count(kw)
    density = (occurrences / word_count * 100) if word_count else 0
    if 0.5 <= density <= 2.0:
        total += 25
    elif 0.3 <= density < 0.5 or 2.0 < density <= 2.5:
        total += 15
        feedback.append(f"Keyword density is {density:.1f}% (ideal: 0.5–2.0%).")
    else:
        total += 5
        feedback.append(f"Keyword density is {density:.1f}%. Adjust usage of '{keyword}'.")

    # ── 2. Heading distribution ────────────────────────────────────────────
    h2_count = len(re.findall(r"^##\s", content, re.MULTILINE))
    h3_count = len(re.findall(r"^###\s", content, re.MULTILINE))
    if h2_count >= 3 and h3_count >= 2:
        total += 20
    elif h2_count >= 2:
        total += 12
        feedback.append("Add more H2/H3 subheadings to improve structure.")
    else:
        total += 4
        feedback.append("Article lacks proper heading structure (H2/H3).")

    # ── 3. Word count (target: 1200–2500 words) ───────────────────────────
    if 1200 <= word_count <= 2500:
        total += 20
    elif 900 <= word_count < 1200 or 2500 < word_count <= 3000:
        total += 12
        feedback.append(f"Word count is {word_count}. Ideal range: 1200–2500.")
    else:
        total += 4
        feedback.append(f"Word count ({word_count}) is outside optimal range (1200–2500).")

    # ── 4. Keyword in first 100 words ─────────────────────────────────────
    intro = " ".join(words[:100]).lower()
    if kw in intro:
        total += 20
    else:
        total += 0
        feedback.append(f"Include '{keyword}' in the first 100 words.")

    # ── 5. Meta optimization ──────────────────────────────────────────────
    meta_score = 0
    if meta_title and kw in meta_title.lower():
        meta_score += 8
    elif not meta_title:
        feedback.append("Missing meta title.")

    if meta_description and kw in meta_description.lower():
        meta_score += 7
    elif not meta_description:
        feedback.append("Missing meta description.")

    if 50 <= len(meta_title) <= 65:
        meta_score = min(meta_score + 0, 15)
    else:
        feedback.append("Meta title should be 50–65 characters.")

    total += min(meta_score, 15)

    return min(total, 100), feedback
