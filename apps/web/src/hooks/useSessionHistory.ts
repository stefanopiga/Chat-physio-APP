import { useState, useEffect } from "react";
import apiClient, { type ConversationMessage } from "../lib/apiClient";

interface UseSessionHistoryResult {
  messages: ConversationMessage[];
  isLoadingHistory: boolean;
  hasMoreMessages: boolean;
  loadMoreHistory: () => Promise<void>;
  error: Error | null;
}

export function useSessionHistory(
  sessionId: string | null
): UseSessionHistoryResult {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [hasMoreMessages, setHasMoreMessages] = useState(false);
  const [currentOffset, setCurrentOffset] = useState(0);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const loadHistory = async () => {
      if (!sessionId) return;

      // Check feature flag (from env or API config)
      const persistentMemoryEnabled =
        import.meta.env.VITE_ENABLE_PERSISTENT_MEMORY === "true";
      if (!persistentMemoryEnabled) {
        console.info("Persistent memory disabled, skipping history load");
        return;
      }

      setIsLoadingHistory(true);
      setError(null);

      try {
        const response = await apiClient.getSessionHistory(sessionId, 100, 0);
        setMessages(response.messages);
        setHasMoreMessages(response.has_more);
        setCurrentOffset(response.messages.length);
      } catch (err) {
        const error = err instanceof Error ? err : new Error("Unknown error");
        setError(error);

        // Graceful degradation: log warning but don't break UI
        console.warn(
          "Failed to load session history, continuing with empty state:",
          error
        );
      } finally {
        setIsLoadingHistory(false);
      }
    };

    loadHistory();
  }, [sessionId]);

  const loadMoreHistory = async () => {
    if (!sessionId || !hasMoreMessages) return;

    try {
      const response = await apiClient.getSessionHistory(
        sessionId,
        100,
        currentOffset
      );
      setMessages((prev) => [...prev, ...response.messages]);
      setHasMoreMessages(response.has_more);
      setCurrentOffset((prev) => prev + response.messages.length);
    } catch (err) {
      console.error("Failed to load more history:", err);
    }
  };

  return {
    messages,
    isLoadingHistory,
    hasMoreMessages,
    loadMoreHistory,
    error,
  };
}

