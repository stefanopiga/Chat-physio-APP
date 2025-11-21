import React, { useCallback, useEffect, useState, useRef } from "react";
import { Menu } from "lucide-react";
import apiClient from "../lib/apiClient";
import ChatInput from "../components/ChatInput";
import ChatMessagesList, {
  type ChatMessage,
} from "../components/ChatMessagesList";
import HelpModal from "../components/HelpModal";
import { useSessionHistory } from "../hooks/useSessionHistory";
import { useSessionStore } from "../store/sessionStore";
import { ChatSidebar } from "../components/ChatSidebar";
import { useHydration } from "../hooks/useHydration";
import { Button } from "../components/ui/button";

const ChatPage: React.FC = () => {
  const hydrated = useHydration();
  const currentSessionId = useSessionStore((state) => state.currentSessionId);
  const setCurrentSession = useSessionStore((state) => state.setCurrentSession);
  const addSession = useSessionStore((state) => state.addSession);
  const sessions = useSessionStore((state) => state.sessions);

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoadingMore, setIsLoadingMore] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isFirstLoad = useRef<boolean>(true);

  // Initialize session if needed
  useEffect(() => {
    if (hydrated && !currentSessionId) {
      if (sessions.length > 0) {
        // Load most recent session
        const sorted = [...sessions].sort(
          (a, b) =>
            new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
        );
        setCurrentSession(sorted[0].id);
      } else {
        // Create new session
        handleNewChat();
      }
    }
  }, [hydrated, currentSessionId, sessions, setCurrentSession, handleNewChat]);

  const handleNewChat = useCallback(() => {
    const newId = crypto.randomUUID();
    const newSession = {
      id: newId,
      title: "Nuova chat",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messageCount: 0,
    };
    addSession(newSession);
    setCurrentSession(newId);
    setMessages([]); // Clear UI immediately
  }, [addSession, setCurrentSession]);

  // Carica history da persistent memory
  const {
    messages: historyMessages,
    isLoadingHistory,
    hasMoreMessages,
    loadMoreHistory,
    error: historyError,
  } = useSessionHistory(currentSessionId || null);

  // Reset messages when session changes
  useEffect(() => {
    setMessages([]);
    isFirstLoad.current = true;
  }, [currentSessionId]);

  // Merge history into current messages (iniziale e pagination)
  useEffect(() => {
    if (historyMessages.length === 0 && isFirstLoad.current) {
      return;
    }

    if (historyMessages.length === 0) return;

    const chatMessages: ChatMessage[] = historyMessages.map((msg) => ({
      id: msg.id,
      role: msg.role,
      content: msg.content,
      citations: msg.metadata?.citations as
        | Array<{ chunk_id: string; score: number }>
        | undefined,
    }));

    if (isFirstLoad.current) {
      setMessages(chatMessages);
      isFirstLoad.current = false;
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "auto" });
      }, 100);
    } else {
      setMessages((prevMessages) => {
        const existingIds = new Set(prevMessages.map((m) => m.id));
        const newMessages = chatMessages.filter((m) => !existingIds.has(m.id));

        if (newMessages.length > 0) {
          return [...newMessages, ...prevMessages];
        }
        return prevMessages;
      });
    }
  }, [historyMessages]);

  // Handler per load more pagination
  const handleLoadMore = useCallback(async () => {
    if (!hasMoreMessages || isLoadingMore) return;

    setIsLoadingMore(true);
    try {
      await loadMoreHistory();
    } catch (error) {
      console.error("Failed to load more history:", error);
    } finally {
      setIsLoadingMore(false);
    }
  }, [hasMoreMessages, isLoadingMore, loadMoreHistory]);

  // Scroll listener per lazy loading pagination (window scroll)
  useEffect(() => {
    if (!hasMoreMessages) return;

    const handleScroll = () => {
      if (window.scrollY < 200 && !isLoadingMore) {
        handleLoadMore();
      }
    };

    let timeoutId: NodeJS.Timeout;
    const debouncedHandleScroll = () => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(handleScroll, 300);
    };

    window.addEventListener("scroll", debouncedHandleScroll);
    return () => {
      clearTimeout(timeoutId);
      window.removeEventListener("scroll", debouncedHandleScroll);
    };
  }, [hasMoreMessages, isLoadingMore, handleLoadMore]);

  // Auto-scroll al bottom quando arrivano nuovi messaggi
  useEffect(() => {
    if (!isFirstLoad.current && !isLoadingMore) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages.length, isLoadingMore]);

  const handleSubmit = useCallback(
    async (question: string) => {
      if (!currentSessionId) return;

      setError(null);
      setLoading(true);

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: question,
      };
      setMessages((prev) => [...prev, userMsg]);

      useSessionStore.getState().updateSession(currentSessionId, {
        messageCount:
          (useSessionStore
            .getState()
            .sessions.find((s) => s.id === currentSessionId)?.messageCount ||
            0) + 1,
        updatedAt: new Date().toISOString(),
      });

      try {
        const sendRes = await apiClient.sendMessage(currentSessionId, question);
        const assistantContent =
          sendRes.message ?? sendRes.answer ?? "Risposta non disponibile.";
        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: assistantContent,
          messageId: sendRes.message_id,
          citations: sendRes.citations,
        };
        setMessages((prev) => [...prev, assistantMsg]);

        useSessionStore.getState().updateSession(currentSessionId, {
          messageCount:
            (useSessionStore
              .getState()
              .sessions.find((s) => s.id === currentSessionId)?.messageCount ||
              0) + 1,
          updatedAt: new Date().toISOString(),
        });
      } catch (e: unknown) {
        const message = e instanceof Error ? e.message : String(e);
        if (message === "401") {
          window.location.href = "/login";
          return;
        }
        if (message === "429")
          setError("Hai superato il limite di richieste. Riprova più tardi.");
        else setError("Si è verificato un errore. Riprova.");
      } finally {
        setLoading(false);
      }
    },
    [currentSessionId]
  );

  if (!hydrated) return null;

  return (
    <div className="min-h-screen flex bg-background">
      <ChatSidebar
        currentSessionId={currentSessionId}
        onSessionSelect={setCurrentSession}
        onNewChat={handleNewChat}
        open={sidebarOpen}
        onOpenChange={setSidebarOpen}
      />

      <div className="flex-1 flex flex-col min-w-0 lg:pl-[300px] transition-[padding] duration-300 ease-in-out">
        <div className="py-8 px-6 border-b bg-background sticky top-0 z-10">
          <div className="flex items-center justify-between max-w-[800px] mx-auto w-full">
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="icon"
                className="lg:hidden shrink-0 -ml-2"
                onClick={() => setSidebarOpen(true)}
              >
                <Menu className="h-5 w-5" />
                <span className="sr-only">Menu</span>
              </Button>
              <h1 className="text-3xl font-bold">Chat</h1>
            </div>
            <div className="flex items-center gap-5">
              <div className="hidden sm:block text-base font-medium opacity-70">
                Sessione:{" "}
                <span className="font-semibold">
                  {currentSessionId?.slice(0, 8) || "-"}
                </span>
              </div>
              <HelpModal />
            </div>
          </div>
        </div>

        <div className="flex-1">
          {isLoadingHistory && currentSessionId && (
            <div className="px-4 pt-2">
              <div className="text-muted-foreground text-sm max-w-[800px] mx-auto flex items-center gap-2">
                <span className="animate-spin">⏳</span>
                Caricamento storico conversazione...
              </div>
            </div>
          )}

          {error && (
            <div className="px-4 pt-2">
              <div
                role="alert"
                className="text-destructive max-w-[800px] mx-auto"
                data-testid="chat-error-message"
              >
                {error}
              </div>
            </div>
          )}

          {historyError && (
            <div className="px-4 pt-2">
              <div
                className="text-muted-foreground text-sm max-w-[800px] mx-auto"
                data-testid="history-warning"
              >
                ⚠️ Impossibile caricare lo storico precedente. Puoi continuare a
                usare la chat normalmente.
              </div>
            </div>
          )}

          <div className="p-4">
            <div className="max-w-[800px] mx-auto">
              {isLoadingMore && (
                <div className="text-muted-foreground text-sm flex items-center justify-center gap-2 py-2">
                  <span className="animate-spin">⏳</span>
                  Caricamento messaggi precedenti...
                </div>
              )}
              <ChatMessagesList messages={messages} loading={loading} />
              <div ref={messagesEndRef} />
            </div>
          </div>
        </div>

        <div className="sticky bottom-0 z-10 p-4 border-t bg-background">
          <div className="max-w-[800px] mx-auto">
            <ChatInput onSubmit={handleSubmit} loading={loading} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
