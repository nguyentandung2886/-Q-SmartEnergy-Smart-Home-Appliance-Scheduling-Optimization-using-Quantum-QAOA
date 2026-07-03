/**
 * Supabase client — handles auth (signup/login/session) for the app.
 * Config comes from VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY (see .env.example).
 */
import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    "Missing Supabase config: set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in client/.env"
  );
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    // Detect the session in the URL after an OAuth redirect (e.g. Google login).
    // This is the supabase-js default; set explicitly so the callback handling is
    // obvious. onAuthStateChange in AuthContext picks up the resulting session.
    detectSessionInUrl: true,
    persistSession: true,
    autoRefreshToken: true,
  },
});
