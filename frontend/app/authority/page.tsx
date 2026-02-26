"use client";
export const dynamic = "force-dynamic";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { getAuthorityScore } from "@/lib/api";
import { logout } from "@/lib/firebase";

export default function AuthorityPage() {
    const { user, loading } = useAuth();
    const router = useRouter();
    const [clusters, setClusters] = useState<any[]>([]);
    const [fetching, setFetching] = useState(true);

    useEffect(() => {
        if (!loading && !user) router.push("/login");
        if (user) {
            getAuthorityScore()
                .then((d) => setClusters(d.clusters ?? []))
                .catch(() => { })
                .finally(() => setFetching(false));
        }
    }, [user, loading, router]);

    return (
        <div style={{ display: "flex" }}>
            <nav className="sidebar">
                <div className="nav-logo">🚀 AutoSEO AI</div>
                <Link href="/dashboard" className="nav-link">📊 Dashboard</Link>
                <Link href="/authority" className="nav-link active">🏆 Authority Score</Link>
                <Link href="/usage" className="nav-link">💰 Token Usage</Link>
                <button className="nav-link" style={{ marginTop: "auto" }} onClick={() => { logout(); router.push("/login"); }}>🚪 Sign out</button>
            </nav>
            <main className="main-content">
                <div className="mb-6">
                    <h1 style={{ marginBottom: 6 }}>🏆 Topical Authority Score</h1>
                    <p className="text-secondary">Your keyword clusters and content coverage across all projects.</p>
                </div>

                {fetching ? (
                    <div className="grid-3">{[1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: 180 }} />)}</div>
                ) : clusters.length === 0 ? (
                    <div className="card" style={{ textAlign: "center", padding: 48 }}>
                        <p style={{ fontSize: "2rem", marginBottom: 12 }}>📊</p>
                        <p className="text-secondary">Create at least 2 keyword projects to see your topical authority clusters.</p>
                        <Link href="/dashboard"><button className="btn btn-primary" style={{ marginTop: 16 }}>Create Projects →</button></Link>
                    </div>
                ) : (
                    <div className="grid-3">
                        {clusters.map((c: any, i: number) => {
                            const pct = Math.round(c.score * 100);
                            const color = pct >= 70 ? "var(--success)" : pct >= 40 ? "var(--warning)" : "var(--danger)";
                            return (
                                <div key={i} className="card">
                                    <div className="flex justify-between items-center mb-3">
                                        <h3 style={{ fontSize: "0.95rem" }}>{c.label}</h3>
                                        <span style={{ fontWeight: 700, fontSize: "1.1rem", color }}>{pct}%</span>
                                    </div>
                                    <div className="progress-bar mb-3">
                                        <div className="progress-fill" style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${color}, ${color}aa)` }} />
                                    </div>
                                    <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginBottom: 12 }}>
                                        {(c.keywords ?? []).map((kw: string, j: number) => (
                                            <span key={j} className="badge badge-draft" style={{ fontSize: "0.7rem" }}>{kw}</span>
                                        ))}
                                    </div>
                                    {c.suggestions?.length > 0 && (
                                        <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10, marginTop: 4 }}>
                                            <p className="text-xs text-muted mb-2">💡 Content suggestions:</p>
                                            {c.suggestions.map((s: string, k: number) => (
                                                <p key={k} className="text-xs" style={{ color: "var(--accent-light)", marginBottom: 4 }}>→ {s}</p>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </main>
        </div>
    );
}
