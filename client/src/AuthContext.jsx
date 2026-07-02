import { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "./supabaseClient";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  async function login(email, password) {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
  }

  async function register(email, password, metadata) {
    // `metadata` lands in the JWT's user_metadata. The backend treats it as
    // user-controlled: a "business" role is honored, but "admin" is ignored.
    const { error } = await supabase.auth.signUp({
      email,
      password,
      ...(metadata ? { options: { data: metadata } } : {}),
    });
    if (error) throw error;
  }

  async function logout() {
    // Local scope: always clears the client session (no server round-trip that
    // can 403 on an already-expired/deleted session).
    await supabase.auth.signOut({ scope: "local" });
  }

  return (
    <AuthContext.Provider
      value={{ session, isAuthenticated: !!session, loading, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
