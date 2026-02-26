/**
 * Firebase client SDK — browser-only.
 *
 * Next.js tries to SSR/prerender every page. Firebase's getAuth() reads
 * NEXT_PUBLIC_* env vars and calls browser APIs that don't exist on the server
 * → crashes with "auth/invalid-api-key" at build time.
 *
 * Fix: guard all Firebase init behind typeof window !== "undefined".
 * All auth helpers return safely when called on the server (they won't be–
 * all pages are "use client" – but the module still imports at build time).
 */
import { initializeApp, getApps, type FirebaseApp } from "firebase/app";
import {
    getAuth,
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    GoogleAuthProvider,
    signInWithPopup,
    signOut,
    onAuthStateChanged,
    type User,
    type Auth,
} from "firebase/auth";

const isClient = typeof window !== "undefined";

let _app: FirebaseApp | undefined;
let _auth: Auth | undefined;

function getFirebase() {
    if (!isClient) return { app: undefined, auth: undefined };
    if (!_auth) {
        const cfg = {
            apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY!,
            authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN!,
            projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID!,
            storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET!,
            messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID!,
            appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID!,
        };
        _app = getApps().length === 0 ? initializeApp(cfg) : getApps()[0];
        _auth = getAuth(_app);
    }
    return { app: _app, auth: _auth };
}

// ── Auth helpers ──────────────────────────────────────────────────────────────

export const loginWithEmail = (email: string, password: string) => {
    const { auth } = getFirebase();
    return signInWithEmailAndPassword(auth!, email, password);
};

export const registerWithEmail = (email: string, password: string) => {
    const { auth } = getFirebase();
    return createUserWithEmailAndPassword(auth!, email, password);
};

export const loginWithGoogle = () => {
    const { auth } = getFirebase();
    return signInWithPopup(auth!, new GoogleAuthProvider());
};

export const logout = () => {
    const { auth } = getFirebase();
    return signOut(auth!);
};

export const onAuthChange = (cb: (user: User | null) => void) => {
    const { auth } = getFirebase();
    if (!auth) return () => { };
    return onAuthStateChanged(auth, cb);
};

export const getIdToken = async (): Promise<string | null> => {
    const { auth } = getFirebase();
    if (!auth) return null;
    const user = auth.currentUser;
    if (!user) return null;
    return user.getIdToken();
};
