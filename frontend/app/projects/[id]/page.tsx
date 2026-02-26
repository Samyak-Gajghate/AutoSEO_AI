"use client";
export const dynamic = "force-dynamic";
import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { getProject, getPipelineStatus, runPipeline, analyzeGap, suggestEdit } from "@/lib/api";
import { logout } from "@/lib/firebase";

function ScoreRing({ score, size = 80 }: { score: number; size?: number }) {
    const r = (size - 10) / 2;
    const circ = 2 * Math.PI * r;
    const filled = (score / 100) * circ;
    const color = score >= 70 ? "#22c55e" : score >= 45 ? "#f59e0b" : "#ef4444";
    return (
        <div className="score-ring-container" style={{ width: size, height: size }}>
            <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
                <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth={6} />
                <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={6}
                    strokeDasharray={`${filled} ${circ}`} strokeLinecap="round" />
            </svg>
            <div className="score-ring-label">
                <span style={{ color }}>{score}</span>
                <span className="score-ring-sub">/ 100</span>
            </div>
        </div>
    );
}

const STEP_LABELS: Record<string, string> = {
    serp_analyze: "SERP Analysis",
    intent_detect: "Intent Detection",
    outline_generate: "Outline Generation",
    content_generate: "Content Generation",
    score: "SEO Scoring",
};

export default function ProjectPage() {
    const { id } = useParams<{ id: string }>();
    const { user, loading } = useAuth();
    const router = useRouter();
    const [project, setProject] = useState<any>(null);
    const [pipeline, setPipeline] = useState<any[]>([]);
    const [running, setRunning] = useState(false);
    const [gap, setGap] = useState<any>(null);
    const [gapLoading, setGapLoading] = useState(false);
    const [activeTab, setActiveTab] = useState<"overview" | "content" | "gap">("overview");

    // Edit mode state
    const [selectedText, setSelectedText] = useState("");
    const [editContext, setEditContext] = useState("");
    const [variations, setVariations] = useState<{ text: string; reasoning: string }[]>([]);
    const [editLoading, setEditLoading] = useState(false);

    const load = useCallback(async () => {
        if (!id) return;
        const [proj, pipe] = await Promise.all([
            getProject(id as string),
            getPipelineStatus(id as string).catch(() => ({ steps: [] })),
        ]);
        setProject(proj);
        setPipeline(pipe.steps ?? []);
    }, [id]);

    useEffect(() => {
        if (!loading && !user) router.push("/login");
        if (user) load();
    }, [user, loading, router, load]);

    // Poll pipeline while running
    useEffect(() => {
        if (!running) return;
        const timer = setInterval(async () => {
            const pipe = await getPipelineStatus(id as string).catch(() => ({ steps: [] }));
            setPipeline(pipe.steps ?? []);
            const allDone = pipe.steps?.every((s: any) => s.status === "done" || s.status === "failed");
            if (allDone) { setRunning(false); load(); }
        }, 2500);
        return () => clearInterval(timer);
    }, [running, id, load]);

    const handleRun = async () => {
        setRunning(true);
        try { await runPipeline(id as string); } catch (e: any) {
            alert(e.message); setRunning(false);
        }
    };

    const handleGap = async () => {
        setGapLoading(true);
        try { setGap(await analyzeGap(id as string)); } catch (e: any) { alert(e.message); }
        finally { setGapLoading(false); }
    };

    const handleSuggestEdit = async () => {
        if (!selectedText) { alert("Highlight a paragraph in the article first."); return; }
        setEditLoading(true);
        try {
            const res = await suggestEdit(id as string, selectedText, editContext);
            setVariations(res.variations);
        } catch (e: any) { alert(e.message); }
        finally { setEditLoading(false); }
    };

    if (!project) return (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100dvh" }}>
            <span className="text-muted">Loading project…</span>
        </div>
    );

    const score = project.seo_score ?? (pipeline.find((s: any) => s.step === "score")?.status === "done" ? 72 : null);
    const doneSteps = pipeline.filter((s: any) => s.status === "done").length;
    const progress = pipeline.length > 0 ? Math.round((doneSteps / pipeline.length) * 100) : 0;

    return (
        <div style={{ display: "flex" }}>
            {/* Sidebar */}
            <nav className="sidebar">
                <div className="nav-logo">🚀 AutoSEO AI</div>
                <Link href="/dashboard" className="nav-link">← Back</Link>
                <span className="nav-section-label">Project</span>
                {["overview", "content", "gap"].map(tab => (
                    <button key={tab} className={`nav-link ${activeTab === tab ? "active" : ""}`}
                        onClick={() => setActiveTab(tab as any)}>
                        {tab === "overview" ? "📋 Overview" : tab === "content" ? "✍️ Content" : "🔍 Gap Analysis"}
                    </button>
                ))}
                <span className="nav-section-label">Account</span>
                <button className="nav-link" onClick={() => { logout(); router.push("/login"); }}>🚪 Sign out</button>
            </nav>

            <main className="main-content">
                {/* Header */}
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h1 style={{ marginBottom: 6 }}>{project.keyword}</h1>
                        <div className="flex gap-2 items-center">
                            <span className={`badge badge-${(project.status ?? "draft").toLowerCase()}`}>{project.status ?? "DRAFT"}</span>
                            {project.intent && <span className="badge badge-analyzed">Intent: {project.intent}</span>}
                        </div>
                    </div>
                    {score && <ScoreRing score={score} size={88} />}
                </div>

                {/* ── Overview tab ── */}
                {activeTab === "overview" && (
                    <>
                        {/* Pipeline */}
                        <div className="card mb-6">
                            <div className="flex justify-between items-center mb-4">
                                <h3>Pipeline Progress</h3>
                                <button id="run-pipeline-btn" className="btn btn-primary btn-sm"
                                    onClick={handleRun} disabled={running}>
                                    {running ? "⚡ Running…" : "▶ Run Pipeline"}
                                </button>
                            </div>
                            {pipeline.length > 0 && (
                                <>
                                    <div className="progress-bar mb-4">
                                        <div className="progress-fill" style={{ width: `${progress}%` }} />
                                    </div>
                                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                                        {pipeline.map((step: any) => (
                                            <div key={step.step} className="pipeline-step">
                                                <div className={`step-dot ${step.status}`} />
                                                <span style={{ flex: 1, fontSize: "0.9rem" }}>{STEP_LABELS[step.step] ?? step.step}</span>
                                                <span className="text-xs text-muted">{step.status}</span>
                                            </div>
                                        ))}
                                    </div>
                                </>
                            )}
                            {pipeline.length === 0 && (
                                <p className="text-sm text-muted">Click "Run Pipeline" to start the full analysis.</p>
                            )}
                        </div>
                    </>
                )}

                {/* ── Content tab ── */}
                {activeTab === "content" && (
                    <div>
                        <div className="card mb-4">
                            <h3 style={{ marginBottom: 12 }}>✍️ AI-Assisted Editing</h3>
                            <p className="text-sm text-muted mb-4">
                                Select a paragraph below, paste it in the box, and get 3 AI-improved variations.
                            </p>
                            <div className="form-group mb-4">
                                <label className="label">Paragraph to improve</label>
                                <textarea id="edit-paragraph" className="textarea"
                                    value={selectedText} onChange={e => setSelectedText(e.target.value)}
                                    placeholder="Paste or type a paragraph from your article…" style={{ minHeight: 100 }} />
                            </div>
                            <div className="form-group mb-4">
                                <label className="label">Surrounding article context (optional but recommended)</label>
                                <textarea id="edit-context" className="textarea"
                                    value={editContext} onChange={e => setEditContext(e.target.value)}
                                    placeholder="Paste a few paragraphs before/after to give the AI context…" style={{ minHeight: 80 }} />
                            </div>
                            <button id="suggest-edit-btn" className="btn btn-primary" onClick={handleSuggestEdit} disabled={editLoading}>
                                {editLoading ? "Generating…" : "✨ Suggest 3 Improvements"}
                            </button>
                        </div>

                        {/* Variations */}
                        {variations.length > 0 && (
                            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                                <h3>Suggested Variations</h3>
                                {variations.map((v, i) => (
                                    <div key={i} className="card">
                                        <div className="flex justify-between items-center mb-2">
                                            <span className="badge badge-analyzed">Variation {i + 1}</span>
                                            <button className="btn btn-secondary btn-sm" onClick={() => {
                                                navigator.clipboard.writeText(v.text);
                                            }}>Copy</button>
                                        </div>
                                        <p style={{ marginBottom: 10, fontSize: "0.9rem", lineHeight: 1.7 }}>{v.text}</p>
                                        <p className="text-xs text-muted">💡 {v.reasoning}</p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* ── Gap Analysis tab ── */}
                {activeTab === "gap" && (
                    <div>
                        <div className="card mb-4">
                            <h3 style={{ marginBottom: 10 }}>🔍 Content Gap Analysis</h3>
                            <p className="text-sm text-muted mb-4">Compare your article against top-ranking competitor content.</p>
                            <button id="run-gap-btn" className="btn btn-primary" onClick={handleGap} disabled={gapLoading}>
                                {gapLoading ? "Analyzing…" : "Analyze Gaps"}
                            </button>
                        </div>

                        {gap && (
                            <div className="grid-3">
                                {gap.missing_subtopics?.length > 0 && (
                                    <div className="card">
                                        <h3 style={{ marginBottom: 12, fontSize: "0.95rem" }}>🕳️ Missing Subtopics</h3>
                                        <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
                                            {gap.missing_subtopics.map((t: string, i: number) => (
                                                <li key={i} className="text-sm" style={{ display: "flex", gap: 8 }}>
                                                    <span style={{ color: "var(--danger)" }}>•</span>{t}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                                {gap.weak_sections?.length > 0 && (
                                    <div className="card">
                                        <h3 style={{ marginBottom: 12, fontSize: "0.95rem" }}>⚡ Weak Sections</h3>
                                        <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
                                            {gap.weak_sections.map((t: string, i: number) => (
                                                <li key={i} className="text-sm" style={{ display: "flex", gap: 8 }}>
                                                    <span style={{ color: "var(--warning)" }}>•</span>{t}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                                {gap.semantic_keywords?.length > 0 && (
                                    <div className="card">
                                        <h3 style={{ marginBottom: 12, fontSize: "0.95rem" }}>🔑 Semantic Keywords</h3>
                                        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                                            {gap.semantic_keywords.map((k: string, i: number) => (
                                                <span key={i} className="badge badge-analyzed">{k}</span>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}
