"use client";
export const dynamic = "force-dynamic";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { getUsageSummary } from "@/lib/api";
import { logout } from "@/lib/firebase";

const FEATURE_ICONS: Record<string, string> = {
    outline: "📝", article: "✍️", score: "📊", edit: "✏️",
    gap: "🔍", authority: "🏆", intent: "🎯",
};

export default function UsagePage() {
    const { user, loading } = useAuth();
    const router = useRouter();
    const [usage, setUsage] = useState<any>(null);
    const [fetching, setFetching] = useState(true);
    const MONTHLY_CAP = 500_000;

    useEffect(() => {
        if (!loading && !user) router.push("/login");
        if (user) {
            getUsageSummary().then(setUsage).catch(() => { }).finally(() => setFetching(false));
        }
    }, [user, loading, router]);

    const pct = usage ? Math.min(Math.round((usage.total_tokens / MONTHLY_CAP) * 100), 100) : 0;
    const pctColor = pct >= 90 ? "var(--danger)" : pct >= 75 ? "var(--warning)" : "var(--success)";

    return (
        <div style={{ display: "flex" }}>
            <nav className="sidebar">
                <div className="nav-logo">🚀 AutoSEO AI</div>
                <Link href="/dashboard" className="nav-link">📊 Dashboard</Link>
                <Link href="/authority" className="nav-link">🏆 Authority Score</Link>
                <Link href="/usage" className="nav-link active">💰 Token Usage</Link>
                <button className="nav-link" style={{ marginTop: "auto" }} onClick={() => { logout(); router.push("/login"); }}>🚪 Sign out</button>
            </nav>
            <main className="main-content">
                <div className="mb-6">
                    <h1 style={{ marginBottom: 6 }}>💰 Token Usage</h1>
                    <p className="text-secondary">AI cost tracking for {usage?.month ?? "this month"}.</p>
                </div>

                {fetching ? (
                    <div className="grid-3">{[1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: 100 }} />)}</div>
                ) : !usage ? (
                    <div className="card" style={{ textAlign: "center", padding: 48 }}>
                        <p className="text-secondary">No usage data yet.</p>
                    </div>
                ) : (
                    <>
                        {/* Summary cards */}
                        <div className="grid-4 mb-6">
                            {[
                                { label: "Total Tokens", value: `${(usage.total_tokens / 1000).toFixed(1)}k`, sub: "this month" },
                                { label: "Estimated Cost", value: `$${usage.total_cost_usd.toFixed(4)}`, sub: "USD" },
                                { label: "Budget Used", value: `${pct}%`, sub: `of 500k cap`, color: pctColor },
                                { label: "Budget Remaining", value: `${((MONTHLY_CAP - usage.total_tokens) / 1000).toFixed(0)}k`, sub: "tokens left" },
                            ].map((c) => (
                                <div key={c.label} className="card card-sm">
                                    <p className="text-xs text-muted mb-1">{c.label}</p>
                                    <p style={{ fontSize: "1.4rem", fontWeight: 700, color: c.color ?? "var(--text-primary)" }}>{c.value}</p>
                                    <p className="text-xs text-muted">{c.sub}</p>
                                </div>
                            ))}
                        </div>

                        {/* Budget progress */}
                        <div className="card mb-6">
                            <div className="flex justify-between items-center mb-3">
                                <h3 style={{ fontSize: "0.95rem" }}>Monthly Budget</h3>
                                <span className="text-sm" style={{ color: pctColor }}>{pct}% used</span>
                            </div>
                            <div className="progress-bar" style={{ height: 10 }}>
                                <div className="progress-fill" style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${pctColor}, ${pctColor}aa)` }} />
                            </div>
                            {pct >= 80 && (
                                <p className="text-xs mt-2" style={{ color: "var(--warning)" }}>
                                    ⚠️ You've used {pct}% of your monthly token budget.
                                </p>
                            )}
                        </div>

                        {/* Per-feature breakdown */}
                        <h2 style={{ marginBottom: 16, fontSize: "1rem" }}>By Feature</h2>
                        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                            {Object.entries(usage.by_feature as Record<string, number>)
                                .sort(([, a], [, b]) => b - a)
                                .map(([feature, tokens]) => {
                                    const featurePct = Math.round((tokens / usage.total_tokens) * 100);
                                    return (
                                        <div key={feature} className="card card-sm">
                                            <div className="flex justify-between items-center mb-2">
                                                <span style={{ fontSize: "0.9rem" }}>
                                                    {FEATURE_ICONS[feature] ?? "🤖"} {feature}
                                                </span>
                                                <div className="flex gap-3 items-center">
                                                    <span className="text-xs text-muted">{(tokens / 1000).toFixed(1)}k tokens</span>
                                                    <span className="badge badge-analyzed">{featurePct}%</span>
                                                </div>
                                            </div>
                                            <div className="progress-bar">
                                                <div className="progress-fill" style={{ width: `${featurePct}%` }} />
                                            </div>
                                        </div>
                                    );
                                })}
                        </div>
                    </>
                )}
            </main>
        </div>
    );
}
