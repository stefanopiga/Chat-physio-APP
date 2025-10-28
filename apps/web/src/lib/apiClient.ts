import { supabase } from "./supabaseClient";

export type QueryChunksResponse = {
  chunks: Array<{
    id: string;
    document_id: string;
    content: string;
    similarity: number;
  }>;
};

export type SendMessageResponse = {
  message_id: string;
  message?: string | null;
  answer?: string | null;
  citations?: Array<{
    chunk_id: string;
    document_id?: string | null;
    excerpt?: string | null;
    position?: number | null;
  }>;
  retrieval_time_ms?: number | null;
  generation_time_ms?: number | null;
};

const API_BASE = "/api/v1";

// In-memory storage for access token (alternativa a sessionStorage per student tokens)
let cachedAccessToken: string | null = null;

async function getAccessToken(): Promise<string> {
  // 1. Try cached token (for student sessions with refresh pattern)
  if (cachedAccessToken) return cachedAccessToken;

  // 2. Try Supabase session (admin users)
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (session?.access_token) return session.access_token;

  // 3. Try sessionStorage (legacy temp JWT)
  try {
    const tmp = sessionStorage.getItem("temp_jwt");
    if (tmp) {
      cachedAccessToken = tmp;
      return tmp;
    }
  } catch {
    // ignore storage errors
  }

  throw new Error("User not authenticated");
}

function setAccessToken(token: string) {
  cachedAccessToken = token;
  try {
    sessionStorage.setItem("temp_jwt", token);
  } catch {
    // ignore storage errors
  }
}

async function refreshAccessToken(): Promise<string | null> {
  /**
   * Refresh Token Pattern (Story 1.3.1).
   * Chiama /api/v1/auth/refresh-token con cookie HttpOnly.
   * Se successo, aggiorna access token cached e ritorna nuovo token.
   * Se fallisce, ritorna null (sessione scaduta/revocata).
   */
  try {
    const response = await fetch(`${API_BASE}/auth/refresh-token`, {
      method: "POST",
      credentials: "include", // Include cookies (refresh token HttpOnly)
    });

    if (!response.ok) return null;

    const data = await response.json();
    const newAccessToken = data.access_token;

    if (newAccessToken) {
      setAccessToken(newAccessToken);
      return newAccessToken;
    }

    return null;
  } catch {
    return null;
  }
}

const apiClient = {
  async get(endpoint: string) {
    const token = await getAccessToken();
    const response = await fetch(endpoint, {
      headers: { Authorization: `Bearer ${token}` },
    });

    // Automatic refresh on 401
    if (response.status === 401) {
      const newToken = await refreshAccessToken();
      if (newToken) {
        // Retry with new token
        const retryResponse = await fetch(endpoint, {
          headers: { Authorization: `Bearer ${newToken}` },
        });
        if (!retryResponse.ok)
          throw new Error(`API call failed: ${retryResponse.status}`);
        return retryResponse.json();
      } else {
        // Refresh failed, session expired
        throw new Error("401");
      }
    }

    if (!response.ok) throw new Error(`API call failed: ${response.status}`);
    return response.json();
  },

  async post<TReq, TRes>(endpoint: string, body: TReq): Promise<TRes> {
    const token = await getAccessToken();
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });

    // Automatic refresh on 401
    if (response.status === 401) {
      const newToken = await refreshAccessToken();
      if (newToken) {
        // Retry with new token
        const retryResponse = await fetch(endpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${newToken}`,
          },
          body: JSON.stringify(body),
        });
        if (retryResponse.status === 401) throw new Error("401");
        if (retryResponse.status === 429) throw new Error("429");
        if (!retryResponse.ok) throw new Error("500");
        return (await retryResponse.json()) as TRes;
      } else {
        // Refresh failed, session expired
        throw new Error("401");
      }
    }

    if (response.status === 429) throw new Error("429");
    if (!response.ok) throw new Error("500");
    return (await response.json()) as TRes;
  },

  async queryChunks(
    sessionId: string,
    question: string,
    options?: { match_threshold?: number; match_count?: number }
  ) {
    const endpoint = `${API_BASE}/chat/query`;
    const payload = { sessionId, question, ...options };
    return this.post<typeof payload, QueryChunksResponse>(endpoint, payload);
  },

  async sendMessage(
    sessionId: string,
    message: string,
    options?: {
      match_threshold?: number;
      match_count?: number;
      chunks?: QueryChunksResponse["chunks"];
    }
  ) {
    const endpoint = `${API_BASE}/chat/sessions/${sessionId}/messages`;
    const payload = {
      message,
      match_threshold: options?.match_threshold,
      match_count: options?.match_count,
      chunks: options?.chunks,
    };
    return this.post<typeof payload, SendMessageResponse>(endpoint, payload);
  },

  async sendFeedback(
    sessionId: string,
    messageId: string,
    vote: "up" | "down"
  ) {
    const endpoint = `${API_BASE}/chat/messages/${messageId}/feedback`;
    const payload = { sessionId, vote };
    return this.post<typeof payload, { ok: boolean }>(endpoint, payload);
  },

  async adminDebugQuery(question: string) {
    const endpoint = `${API_BASE}/admin/debug/query`;
    const payload = { question };
    return this.post<
      typeof payload,
      {
        question: string;
        answer: string | null;
        chunks: Array<{
          chunk_id: string | null;
          content: string | null;
          similarity_score: number | null;
          metadata: {
            document_id?: string | null;
            document_name?: string | null;
            page_number?: number | null;
            chunking_strategy?: string | null;
          } | null;
        }>;
        retrieval_time_ms: number;
        generation_time_ms: number;
      }
    >(endpoint, payload);
  },
};

export default apiClient;
