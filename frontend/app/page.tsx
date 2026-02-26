"use client";
export const dynamic = "force-dynamic";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function RootPage() {
    const { user, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!loading) {
            router.replace(user ? "/dashboard" : "/login");
        }
    }, [user, loading, router]);

    return (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100dvh" }}>
            <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>🚀</div>
                <p className="text-muted text-sm">Loading AutoSEO AI…</p>
            </div>
        </div>
    );
}
