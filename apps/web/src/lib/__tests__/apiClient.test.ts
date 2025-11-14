import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import apiClient, {
  type SessionHistoryResponse,
  type ConversationMessage,
} from "../apiClient";

// Mock supabaseClient per auth
vi.mock("../supabaseClient", () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: {
          session: {
            access_token: "test-token",
          },
        },
      }),
    },
  },
}));

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("apiClient.getSessionHistory", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("ritorna history con success", async () => {
    const mockMessages: ConversationMessage[] = [
      {
        id: "1",
        role: "user",
        content: "Test question",
        metadata: {},
        created_at: "2025-01-01T00:00:00Z",
      },
      {
        id: "2",
        role: "assistant",
        content: "Test answer",
        metadata: {},
        created_at: "2025-01-01T00:00:01Z",
      },
    ];

    const mockResponse: SessionHistoryResponse = {
      messages: mockMessages,
      total_count: 2,
      has_more: false,
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockResponse,
    });

    const result = await apiClient.getSessionHistory("test-session-id", 100, 0);

    expect(result).toEqual(mockResponse);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/chat/sessions/test-session-id/history/full?limit=100&offset=0",
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          Authorization: "Bearer test-token",
        }),
      })
    );
  });

  it("ritorna empty array per sessione nuova (404)", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
    });

    const result = await apiClient.getSessionHistory("new-session-id");

    expect(result).toEqual({
      messages: [],
      total_count: 0,
      has_more: false,
    });
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("gestisce network error con 3 retry", async () => {
    mockFetch
      .mockRejectedValueOnce(new TypeError("fetch failed"))
      .mockRejectedValueOnce(new TypeError("fetch failed"))
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          messages: [],
          total_count: 0,
          has_more: false,
        }),
      });

    const resultPromise = apiClient.getSessionHistory("test-session-id");

    // Fast-forward attraverso i 2 retry (1s + 2s)
    await vi.advanceTimersByTimeAsync(1000);
    await vi.advanceTimersByTimeAsync(2000);

    const result = await resultPromise;

    expect(result).toEqual({
      messages: [],
      total_count: 0,
      has_more: false,
    });
    expect(mockFetch).toHaveBeenCalledTimes(3); // Original + 2 retry
  });

  it("fallisce dopo 3 retry su network error persistente", async () => {
    mockFetch
      .mockRejectedValueOnce(new TypeError("fetch failed"))
      .mockRejectedValueOnce(new TypeError("fetch failed"))
      .mockRejectedValueOnce(new TypeError("fetch failed"))
      .mockRejectedValueOnce(new TypeError("fetch failed")); // 4th attempt after 3 retries

    const resultPromise = apiClient.getSessionHistory("test-session-id");

    // Fast-forward attraverso tutti i retry (0→1→2→3)
    await vi.advanceTimersByTimeAsync(1000); // retry 1
    await vi.advanceTimersByTimeAsync(2000); // retry 2
    await vi.advanceTimersByTimeAsync(4000); // retry 3 (final)

    await expect(resultPromise).rejects.toThrow();
    expect(mockFetch).toHaveBeenCalledTimes(4); // Initial + 3 retries
  });

  it("gestisce 429 rate limit con retry ed exponential backoff", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: false,
        status: 429,
        headers: new Headers({ "Retry-After": "2" }), // 2 secondi
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          messages: [],
          total_count: 0,
          has_more: false,
        }),
      });

    const resultPromise = apiClient.getSessionHistory("test-session-id");

    // Fast-forward Retry-After delay
    await vi.advanceTimersByTimeAsync(2000);

    const result = await resultPromise;

    expect(result).toEqual({
      messages: [],
      total_count: 0,
      has_more: false,
    });
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("fallisce dopo 3 retry su 429 persistente", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: false,
        status: 429,
        headers: new Headers(),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 429,
        headers: new Headers(),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 429,
        headers: new Headers(),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 429,
        headers: new Headers(),
      }); // 4th attempt after 3 retries

    const resultPromise = apiClient.getSessionHistory("test-session-id");

    // Fast-forward attraverso tutti i backoff (0→1→2→3)
    await vi.advanceTimersByTimeAsync(1000); // retry 1
    await vi.advanceTimersByTimeAsync(2000); // retry 2
    await vi.advanceTimersByTimeAsync(4000); // retry 3 (final)

    await expect(resultPromise).rejects.toThrow("429");
    expect(mockFetch).toHaveBeenCalledTimes(4); // Initial + 3 retries
  });

  it("gestisce 500 server error", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: async () => "Internal Server Error",
    });

    await expect(
      apiClient.getSessionHistory("test-session-id")
    ).rejects.toThrow("HTTP 500");
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("testa pagination con limit e offset custom", async () => {
    const mockResponse: SessionHistoryResponse = {
      messages: [
        {
          id: "101",
          role: "user",
          content: "Page 2 message",
          metadata: {},
          created_at: "2025-01-02T00:00:00Z",
        },
      ],
      total_count: 150,
      has_more: true,
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockResponse,
    });

    const result = await apiClient.getSessionHistory(
      "test-session-id",
      50,
      100
    );

    expect(result).toEqual(mockResponse);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/chat/sessions/test-session-id/history/full?limit=50&offset=100",
      expect.any(Object)
    );
  });
});

