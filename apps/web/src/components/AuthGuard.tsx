import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { authService } from "../services/authService";
import type { Session } from "@supabase/supabase-js";

const AuthGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasTempToken, setHasTempToken] = useState<boolean>(false);

  const navigate = useNavigate();

  // Legge presenza di token temporaneo immediatamente al primo render
  useEffect(() => {
    try {
      const token = sessionStorage.getItem("temp_jwt");
      setHasTempToken(Boolean(token));
    } catch {
      setHasTempToken(false);
    }
  }, []);

  useEffect(() => {
    const {
      data: { subscription },
    } = authService.onAuthStateChange((_event, session) => {
      setSession(session);
      setLoading(false);
    });

    // Controlla la sessione iniziale
    authService.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!loading && !session && !hasTempToken) {
      navigate("/");
    }
  }, [loading, session, hasTempToken, navigate]);

  if (loading || (!session && !hasTempToken)) {
    return <div>Verifica autenticazione...</div>;
  }

  return <>{children}</>;
};

export default AuthGuard;
