"use client";
export const dynamic = "force-dynamic";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { logout } from "@/lib/firebase";
import { listProjects, createProject, getAuthorityScore, getUsageSummary } from "@/lib/api";

function ScoreRing({ score, size = 72 }: { score: number; size?: number }) {
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

function StatusBadge({ status }: { status: string }) {
    return <span className={`badge badge-${status.toLowerCase()}`}>{status}</span>;
}

function Sidebar({ activeHref }: { activeHref: string }) {
    const router = useRouter();
    const handleLogout = async () => { await logout(); router.push("/login"); };
    return (
        <nav className="sidebar">
            <div className="nav-logo">🚀 AutoSEO AI</div>
            <span className="nav-section-label">Main</span>
            <Link href="/dashboard" className={`nav-link ${activeHref === "/dashboard" ? "active" : ""}`}>
                📊 Dashboard
            </Link>
            <Link href="/authority" className={`nav-link ${activeHref === "/authority" ? "active" : ""}`}>
                🏆 Authority Score
            </Link>
            <span className="nav-section-label">Account</span>
            <Link href="/usage" className={`nav-link ${activeHref === "/usage" ? "active" : ""}`}>
                💰 Token Usage
            </Link>
            <button className="nav-link" onClick={handleLogout} style={{ marginTop: "auto" }}>
                🚪 Sign out
            </button>
        </nav>
    );
}

export default function DashboardPage() {
    const { user, loading } = useAuth();
    const router = useRouter();
    const [projects, setProjects] = useState<any[]>([]);
    const [keyword, setKeyword] = useState("");
    const [creating, setCreating] = useState(false);
    const [usage, setUsage] = useState<any>(null);
    const [projLoading, setProjLoading] = useState(true);

    useEffect(() => {
        if (!loading && !user) router.push("/login");
    }, [user, loading, router]);

    useEffect(() => {
        if (!user) return;
        listProjects().then(setProjects).finally(() => setProjLoading(false));
        getUsageSummary().then(setUsage).catch(() => { });
    }, [user]);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!keyword.trim()) return;
        setCreating(true);
        try {
            const proj = await createProject(keyword.trim());
            router.push(`/projects/${proj.id}`);
        } catch (err: any) {
            alert(err.message);
        } finally { setCreating(false); }
    };

    if (loading || !user) return (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100dvh" }}>
            <span className="text-muted">Loading…</span>
        </div>
    );

    return (
        <div style={{ display: "flex" }}>
            <Sidebar activeHref="/dashboard" />
            <main className="main-content">
                {/* Header */}
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h1 style={{ marginBottom: 4 }}>Dashboard</h1>
                        <p className="text-sm text-muted">{user.email}</p>
                    </div>
                    {usage && (
                        <div className="card card-sm" style={{ textAlign: "right", minWidth: 180 }}>
                            <p className="text-xs text-muted">This month</p>
                            <p className="font-bold" style={{ color: "var(--accent-light)" }}>
                                {(usage.total_tokens / 1000).toFixed(1)}k tokens
                            </p>
                            <p className="text-xs text-muted">${usage.total_cost_usd.toFixed(4)} USD</p>
                        </div>
                    )}
                </div>

                {/* New project */}
                <div className="card mb-6">
                    <h3 style={{ marginBottom: 14 }}>✨ New Keyword Project</h3>
                    <form onSubmit={handleCreate} style={{ display: "flex", gap: 12 }}>
                        <input id="keyword-input" className="input" value={keyword}
                            onChange={(e) => setKeyword(e.target.value)}
                            placeholder="e.g. Best CRM software for startups" style={{ flex: 1 }} />
                        <button id="create-project-btn" type="submit" className="btn btn-primary" disabled={creating}>
                            {creating ? "Creating…" : "Analyze →"}
                        </button>
                    </form>
                    <p className="text-xs text-muted mt-2">Enter any keyword. We'll scrape SERP, detect intent, and generate an SEO-optimized article.</p>
                </div>

                {/* Projects grid */}
                <h2 style={{ marginBottom: 16, fontSize: "1.1rem" }}>Your Projects</h2>
                {projLoading ? (
                    <div className="grid-3">
                        {[1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: 140 }} />)}
                    </div>
                ) : projects.length === 0 ? (
                    <div className="card" style={{ textAlign: "center", padding: 48 }}>
                        <p style={{ fontSize: "2rem", marginBottom: 12 }}>🎯</p>
                        <p className="text-secondary">No projects yet. Enter a keyword above to get started.</p>
                    </div>
                ) : (
                    <div className="grid-3">
                        {projects.map((p) => (
                            <Link key={p.id} href={`/projects/${p.id}`} style={{ textDecoration: "none" }}>
                                <div className="card" style={{ cursor: "pointer" }}>
                                    <div className="flex justify-between items-center mb-2">
                                        <StatusBadge status={p.status ?? "DRAFT"} />
                                        {p.seo_score ? <ScoreRing score={p.seo_score} size={48} /> : null}
                                    </div>
                                    <h3 style={{ fontSize: "0.95rem", marginBottom: 6, marginTop: 8 }}>{p.keyword}</h3>
                                    {p.intent && (
                                        <p className="text-xs" style={{ color: "var(--accent-light)" }}>
                                            Intent: {p.intent}
                                        </p>
                                    )}
                                    <p className="text-xs text-muted mt-2">
                                        {p.created_at ? new Date(p.created_at._seconds * 1000).toLocaleDateString() : ""}
                                    </p>
                                </div>
                            </Link>
                        ))}
                    </div>
                )}
            </main>
        </div>
    );
}
