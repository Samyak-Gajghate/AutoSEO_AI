import { getIdToken } from "@/lib/firebase";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

async function request<T>(
    path: string,
    options: RequestInit = {}
): Promise<T> {
    const token = await getIdToken();
    const res = await fetch(`${BASE_URL}${path}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(options.headers ?? {}),
        },
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? "Request failed");
    }
    return res.json();
}

// ── Projects ──────────────────────────────────────────────────────────────────

export const createProject = (keyword: string) =>
    request<{ id: string; keyword: string }>("/projects", {
        method: "POST",
        body: JSON.stringify({ keyword }),
    });

export const listProjects = () => request<any[]>("/projects");

export const getProject = (id: string) => request<any>(`/projects/${id}`);

export const getPipelineStatus = (id: string) =>
    request<{ project_id: string; steps: any[] }>(`/projects/${id}/pipeline`);

export const runPipeline = (id: string) =>
    request<any>(`/projects/${id}/run`, { method: "POST" });

// ── Gap Analysis ──────────────────────────────────────────────────────────────

export const analyzeGap = (projectId: string) =>
    request<any>(`/projects/${projectId}/analyze-gap`, { method: "POST" });

// ── AI-Assisted Editing ───────────────────────────────────────────────────────

export const suggestEdit = (
    projectId: string,
    paragraph: string,
    surrounding_context: string
) =>
    request<{ variations: { text: string; reasoning: string }[] }>("/suggest-edit", {
        method: "POST",
        body: JSON.stringify({ project_id: projectId, paragraph, surrounding_context }),
    });

// ── Authority Score ───────────────────────────────────────────────────────────

export const getAuthorityScore = () => request<any>("/authority-score");

// ── Token Usage ───────────────────────────────────────────────────────────────

export const getUsageSummary = () =>
    request<{
        total_tokens: number;
        total_cost_usd: number;
        by_feature: Record<string, number>;
        month: string;
    }>("/usage");
