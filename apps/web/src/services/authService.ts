import { supabase } from "@/lib/supabaseClient";
import type { Session, AuthChangeEvent } from "@supabase/supabase-js";

/**
 * Interfaccia per il servizio di autenticazione.
 * Definisce il contratto indipendente dal provider di autenticazione.
 */
export interface IAuthService {
  /**
   * Recupera la sessione corrente dell'utente.
   * @returns Promise contenente dati sessione o errore
   */
  getSession(): Promise<{ data: { session: Session | null }; error: unknown }>;

  /**
   * Registra callback per cambiamenti di stato autenticazione.
   * @param callback - Funzione chiamata ad ogni cambio stato
   * @returns Oggetto subscription per cleanup
   */
  onAuthStateChange(
    callback: (event: AuthChangeEvent, session: Session | null) => void
  ): { data: { subscription: { unsubscribe: () => void } } };

  /**
   * Verifica se la sessione corrente appartiene a un admin.
   * @param session - Oggetto sessione da verificare
   * @returns true se utente è admin
   */
  isAdmin(session: Session | null): boolean;

  /**
   * Verifica se la sessione corrente appartiene a uno studente.
   * @param session - Oggetto sessione da verificare
   * @returns true se utente è student
   */
  isStudent(session: Session | null): boolean;

  /**
   * Verifica se esiste una sessione autenticata valida.
   * @param session - Oggetto sessione da verificare
   * @returns true se sessione valida
   */
  isAuthenticated(session: Session | null): boolean;
}

/**
 * Implementazione del servizio di autenticazione con Supabase.
 * Wrapper che disaccoppia l'applicazione dal client Supabase.
 */
class AuthService implements IAuthService {
  private client = supabase;

  async getSession(): Promise<{
    data: { session: Session | null };
    error: unknown;
  }> {
    return this.client.auth.getSession();
  }

  onAuthStateChange(
    callback: (event: AuthChangeEvent, session: Session | null) => void
  ) {
    return this.client.auth.onAuthStateChange(callback);
  }

  isAdmin(session: Session | null): boolean {
    if (!session) return false;
    const role = session.user?.app_metadata?.role as string | undefined;
    return role === "admin";
  }

  isStudent(session: Session | null): boolean {
    if (!session) return false;
    const role = session.user?.app_metadata?.role as string | undefined;
    return role === "student";
  }

  isAuthenticated(session: Session | null): boolean {
    return session !== null;
  }
}

/**
 * Istanza singleton del servizio di autenticazione.
 * Utilizzare questa istanza in tutta l'applicazione.
 * In ambiente test, può essere sostituito da __mockAuthService.
 */
export const authService: IAuthService =
  typeof window !== "undefined" &&
  (window as { __mockAuthService?: IAuthService }).__mockAuthService
    ? (window as unknown as { __mockAuthService: IAuthService })
        .__mockAuthService
    : new AuthService();
