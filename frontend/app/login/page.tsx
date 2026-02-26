"use client";
export const dynamic = "force-dynamic";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { loginWithEmail, registerWithEmail, loginWithGoogle } from "@/lib/firebase";

export default function LoginPage() {
    const router = useRouter();
    const [mode, setMode] = useState<"login" | "register">("login");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(""); setLoading(true);
        try {
            if (mode === "login") await loginWithEmail(email, password);
            else await registerWithEmail(email, password);
            router.push("/dashboard");
        } catch (err: any) {
            setError(err.message ?? "Authentication failed");
        } finally { setLoading(false); }
    };

    const googleLogin = async () => {
        setError(""); setLoading(true);
        try { await loginWithGoogle(); router.push("/dashboard"); }
        catch (err: any) { setError(err.message); }
        finally { setLoading(false); }
    };

    return (
        <div style={{ minHeight: "100dvh", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
            {/* Ambient glow */}
            <div style={{
                position: "fixed", top: "20%", left: "50%", transform: "translateX(-50%)",
                width: 600, height: 300, borderRadius: "50%",
                background: "radial-gradient(ellipse, rgba(99,102,241,0.12), transparent 70%)",
                pointerEvents: "none",
            }} />

            <div className="card" style={{ width: "100%", maxWidth: 440, padding: 36 }}>
                {/* Logo */}
                <div style={{ textAlign: "center", marginBottom: 32 }}>
                    <div style={{
                        width: 52, height: 52, borderRadius: 14,
                        background: "linear-gradient(135deg, var(--accent), var(--accent-light))",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 24, margin: "0 auto 14px",
                    }}>🚀</div>
                    <h1 style={{ fontSize: "1.5rem", marginBottom: 4 }}>AutoSEO AI</h1>
                    <p className="text-muted text-sm">
                        {mode === "login" ? "Welcome back" : "Create your account"}
                    </p>
                </div>

                {/* Google */}
                <button id="google-login-btn" className="btn btn-secondary" style={{ width: "100%", justifyContent: "center", marginBottom: 16 }}
                    onClick={googleLogin} disabled={loading}>
                    <svg width="18" height="18" viewBox="0 0 48 48"><path fill="#FFC107" d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z" /><path fill="#FF3D00" d="m6.306 14.691 6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 16.318 4 9.656 8.337 6.306 14.691z" /><path fill="#4CAF50" d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238A11.91 11.91 0 0 1 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z" /><path fill="#1976D2" d="M43.611 20.083H42V20H24v8h11.303a12.04 12.04 0 0 1-4.087 5.571l.003-.002 6.19 5.238C36.971 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917z" /></svg>
                    Continue with Google
                </button>

                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
                    <div className="divider" style={{ margin: 0, flex: 1 }} />
                    <span className="text-muted text-xs">or</span>
                    <div className="divider" style={{ margin: 0, flex: 1 }} />
                </div>

                {/* Form */}
                <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                    <div className="form-group">
                        <label className="label" htmlFor="email">Email</label>
                        <input id="email" type="email" className="input" value={email}
                            onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" required />
                    </div>
                    <div className="form-group">
                        <label className="label" htmlFor="password">Password</label>
                        <input id="password" type="password" className="input" value={password}
                            onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required />
                    </div>

                    {error && (
                        <div style={{
                            background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
                            borderRadius: "var(--radius-md)", padding: "10px 14px",
                            color: "var(--danger)", fontSize: "0.85rem",
                        }}>{error}</div>
                    )}

                    <button id="auth-submit-btn" type="submit" className="btn btn-primary btn-lg"
                        style={{ justifyContent: "center", marginTop: 4 }} disabled={loading}>
                        {loading ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
                    </button>
                </form>

                <p className="text-sm text-muted" style={{ textAlign: "center", marginTop: 20 }}>
                    {mode === "login" ? "No account? " : "Already have one? "}
                    <button className="btn-ghost" style={{ display: "inline", padding: 0, color: "var(--accent-light)", fontSize: "0.85rem", background: "none", border: "none", cursor: "pointer" }}
                        onClick={() => setMode(mode === "login" ? "register" : "login")}>
                        {mode === "login" ? "Sign up" : "Sign in"}
                    </button>
                </p>
            </div>
        </div>
    );
}
