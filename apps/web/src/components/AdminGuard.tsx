import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { authService } from "../services/authService";
import type { Session } from "@supabase/supabase-js";

const AdminGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const {
      data: { subscription },
    } = authService.onAuthStateChange((_event, session) => {
      setSession(session);
      setLoading(false);
    });

    authService.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!loading) {
      if (!session || !authService.isAdmin(session)) {
        navigate("/login");
      }
    }
  }, [loading, session, navigate]);

  if (loading || !session || !authService.isAdmin(session)) {
    return <div>Verifica autorizzazione amministratore...</div>;
  }

  return <>{children}</>;
};

export default AdminGuard;
