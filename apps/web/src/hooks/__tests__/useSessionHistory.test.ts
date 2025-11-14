import { renderHook, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { useSessionHistory } from "../useSessionHistory";
import apiClient from "../../lib/apiClient";

vi.mock("../../lib/apiClient");

describe("useSessionHistory", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv("VITE_ENABLE_PERSISTENT_MEMORY", "true");
  });

  it("carica history on mount con success", async () => {
    const mockMessages = [
      {
        id: "1",
        role: "user" as const,
        content: "Test",
        metadata: {},
        created_at: "2025-01-01T00:00:00Z",
      },
    ];

    vi.mocked(apiClient.getSessionHistory).mockResolvedValue({
      messages: mockMessages,
      total_count: 1,
      has_more: false,
    });

    const { result } = renderHook(() => useSessionHistory("test-session"));

    expect(result.current.isLoadingHistory).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoadingHistory).toBe(false);
    });

    expect(result.current.messages).toEqual(mockMessages);
    expect(result.current.error).toBeNull();
    expect(result.current.hasMoreMessages).toBe(false);
  });

  it("gestisce sessione vuota (empty array)", async () => {
    vi.mocked(apiClient.getSessionHistory).mockResolvedValue({
      messages: [],
      total_count: 0,
      has_more: false,
    });

    const { result } = renderHook(() => useSessionHistory("empty-session"));

    await waitFor(() => {
      expect(result.current.isLoadingHistory).toBe(false);
    });

    expect(result.current.messages).toEqual([]);
    expect(result.current.error).toBeNull();
    expect(result.current.hasMoreMessages).toBe(false);
  });

  it("gestisce network error con graceful degradation", async () => {
    const consoleWarnSpy = vi
      .spyOn(console, "warn")
      .mockImplementation(() => {});

    vi.mocked(apiClient.getSessionHistory).mockRejectedValue(
      new Error("Network error")
    );

    const { result } = renderHook(() => useSessionHistory("test-session"));

    await waitFor(() => {
      expect(result.current.isLoadingHistory).toBe(false);
    });

    expect(result.current.messages).toEqual([]);
    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe("Network error");
    expect(consoleWarnSpy).toHaveBeenCalledWith(
      "Failed to load session history, continuing with empty state:",
      expect.any(Error)
    );

    consoleWarnSpy.mockRestore();
  });

  it("gestisce server error con graceful degradation", async () => {
    const consoleWarnSpy = vi
      .spyOn(console, "warn")
      .mockImplementation(() => {});

    vi.mocked(apiClient.getSessionHistory).mockRejectedValue(
      new Error("HTTP 500: Internal Server Error")
    );

    const { result } = renderHook(() => useSessionHistory("test-session"));

    await waitFor(() => {
      expect(result.current.isLoadingHistory).toBe(false);
    });

    expect(result.current.messages).toEqual([]);
    expect(result.current.error).toBeInstanceOf(Error);
    expect(consoleWarnSpy).toHaveBeenCalled();

    consoleWarnSpy.mockRestore();
  });

  it("skip caricamento se sessionId è null", async () => {
    const { result } = renderHook(() => useSessionHistory(null));

    await waitFor(() => {
      expect(result.current.isLoadingHistory).toBe(false);
    });

    expect(apiClient.getSessionHistory).not.toHaveBeenCalled();
    expect(result.current.messages).toEqual([]);
  });

  it("skip caricamento se feature flag disabled", async () => {
    vi.stubEnv("VITE_ENABLE_PERSISTENT_MEMORY", "false");

    const consoleInfoSpy = vi
      .spyOn(console, "info")
      .mockImplementation(() => {});

    const { result } = renderHook(() => useSessionHistory("test-session"));

    await waitFor(() => {
      expect(result.current.isLoadingHistory).toBe(false);
    });

    expect(apiClient.getSessionHistory).not.toHaveBeenCalled();
    expect(consoleInfoSpy).toHaveBeenCalledWith(
      "Persistent memory disabled, skipping history load"
    );

    consoleInfoSpy.mockRestore();
  });

  it("loadMoreHistory carica paginazione successiva", async () => {
    const initialMessages = [
      {
        id: "1",
        role: "user" as const,
        content: "Message 1",
        metadata: {},
        created_at: "2025-01-01T00:00:00Z",
      },
    ];

    const moreMessages = [
      {
        id: "2",
        role: "assistant" as const,
        content: "Message 2",
        metadata: {},
        created_at: "2025-01-01T00:00:01Z",
      },
    ];

    vi.mocked(apiClient.getSessionHistory)
      .mockResolvedValueOnce({
        messages: initialMessages,
        total_count: 2,
        has_more: true,
      })
      .mockResolvedValueOnce({
        messages: moreMessages,
        total_count: 2,
        has_more: false,
      });

    const { result } = renderHook(() => useSessionHistory("test-session"));

    await waitFor(() => {
      expect(result.current.isLoadingHistory).toBe(false);
    });

    expect(result.current.messages).toEqual(initialMessages);
    expect(result.current.hasMoreMessages).toBe(true);

    await result.current.loadMoreHistory();

    await waitFor(() => {
      expect(result.current.messages).toEqual([
        ...initialMessages,
        ...moreMessages,
      ]);
    });

    expect(result.current.hasMoreMessages).toBe(false);
    expect(apiClient.getSessionHistory).toHaveBeenCalledTimes(2);
    expect(apiClient.getSessionHistory).toHaveBeenNthCalledWith(
      2,
      "test-session",
      100,
      1
    );
  });

  it("loadMoreHistory skip se hasMoreMessages false", async () => {
    vi.mocked(apiClient.getSessionHistory).mockResolvedValue({
      messages: [],
      total_count: 0,
      has_more: false,
    });

    const { result } = renderHook(() => useSessionHistory("test-session"));

    await waitFor(() => {
      expect(result.current.isLoadingHistory).toBe(false);
    });

    vi.clearAllMocks();

    await result.current.loadMoreHistory();

    expect(apiClient.getSessionHistory).not.toHaveBeenCalled();
  });
});
