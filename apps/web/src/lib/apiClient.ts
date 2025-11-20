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

export type ConversationMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  source_chunk_ids?: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type SessionHistoryResponse = {
  messages: ConversationMessage[];
  total_count: number;
  has_more: boolean;
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

// Simple in-memory cache for GET requests (5 min TTL)
const requestCache = new Map<string, { data: unknown; timestamp: number }>();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

const apiClient = {
  async get(endpoint: string, useCache = false) {
    // Check cache first if enabled
    if (useCache) {
      const cached = requestCache.get(endpoint);
      if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
        return cached.data;
      }
    }

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
    const data = await response.json();
    
    // Store in cache if enabled
    if (useCache) {
      requestCache.set(endpoint, { data, timestamp: Date.now() });
    }
    
    return data;
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

  async getSessionHistory(
    sessionId: string,
    limit: number = 100,
    offset: number = 0
  ): Promise<SessionHistoryResponse> {
    const endpoint = `${API_BASE}/chat/sessions/${sessionId}/history/full?limit=${limit}&offset=${offset}`;

    const attemptFetch = async (
      attemptNumber: number
    ): Promise<SessionHistoryResponse> => {
      let response: Response | undefined;

      try {
        const token = await getAccessToken();
        response = await fetch(endpoint, {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        });
      } catch (error) {
        // Network errors - retry with exponential backoff
        if (
          error instanceof TypeError &&
          attemptNumber < 3
        ) {
          const delay = Math.pow(2, attemptNumber) * 1000; // 1s, 2s, 4s
          console.warn(`Network error, retrying after ${delay / 1000}s`);
          await new Promise((resolve) => setTimeout(resolve, delay));
          return attemptFetch(attemptNumber + 1);
        }

        throw error;
      }

      // Guard: if response is undefined after catch, re-throw error
      if (!response) {
        throw new Error("Network request failed after retries");
      }

      // Handle 404 - nuova sessione, return empty
      if (response.status === 404) {
        return { messages: [], total_count: 0, has_more: false };
      }

      // Handle 401 - try refresh token once
      if (response.status === 401) {
        const newToken = await refreshAccessToken();
        if (newToken) {
          const retryResponse = await fetch(endpoint, {
            method: "GET",
            headers: {
              Authorization: `Bearer ${newToken}`,
              "Content-Type": "application/json",
            },
          });

          if (retryResponse.status === 404) {
            return { messages: [], total_count: 0, has_more: false };
          }

          if (!retryResponse.ok) {
            throw new Error(`HTTP ${retryResponse.status}`);
          }

          return (await retryResponse.json()) as SessionHistoryResponse;
        } else {
          // Refresh failed, redirect to login
          window.location.href = "/";
          throw new Error("Unauthorized");
        }
      }

      // Handle 429 - rate limit, retry with exponential backoff
      if (response.status === 429) {
        const retryAfterHeader = response.headers.get("Retry-After");
        const retryAfter = retryAfterHeader
          ? parseInt(retryAfterHeader, 10) * 1000
          : Math.pow(2, attemptNumber) * 1000; // 1s, 2s, 4s

        if (attemptNumber < 3) {
          console.warn(
            `Rate limit exceeded, retrying after ${retryAfter / 1000}s`
          );
          await new Promise((resolve) => setTimeout(resolve, retryAfter));
          return attemptFetch(attemptNumber + 1);
        }

        throw new Error("429");
      }

      // Handle other errors
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      return (await response.json()) as SessionHistoryResponse;
    };

    return attemptFetch(0);
  },
};

export default apiClient;
