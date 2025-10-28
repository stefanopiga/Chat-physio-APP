import { createClient } from "@supabase/supabase-js";

// È consigliabile utilizzare variabili d'ambiente per questi valori
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

const options = {
  auth: {
    autoRefreshToken: false, // MODIFICATO: Disabilitato per risolvere l'errore
    persistSession: true,
    detectSessionInUrl: true,
  },
};

export const supabase = createClient(supabaseUrl, supabaseAnonKey, options);
