import React, { useCallback, useEffect, useState, useRef } from "react";
import apiClient from "../lib/apiClient";
import ChatInput from "../components/ChatInput";
import ChatMessagesList, {
  type ChatMessage,
} from "../components/ChatMessagesList";
import HelpModal from "../components/HelpModal";
import { useSessionHistory } from "../hooks/useSessionHistory";

const SESSION_KEY = "chat.sessionId";

function getOrCreateSessionId(): string {
  let s = localStorage.getItem(SESSION_KEY);
  if (!s) {
    s = crypto.randomUUID();
    localStorage.setItem(SESSION_KEY, s);
  }
  return s;
}

const ChatPage: React.FC = () => {
  // CRITICAL FIX: Initialize sessionId immediately to prevent null on first render
  const [sessionId] = useState<string>(() => getOrCreateSessionId());
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoadingMore, setIsLoadingMore] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const isFirstLoad = useRef<boolean>(true);

  // Carica history da persistent memory
  const {
    messages: historyMessages,
    isLoadingHistory,
    hasMoreMessages,
    loadMoreHistory,
    error: historyError,
  } = useSessionHistory(sessionId || null);

  // Merge history into current messages (iniziale e pagination)
  useEffect(() => {
    if (historyMessages.length === 0) return;

    // Converti ConversationMessage[] da backend a ChatMessage[] per UI
    const chatMessages: ChatMessage[] = historyMessages.map((msg) => ({
      id: msg.id,
      role: msg.role,
      content: msg.content,
      // metadata contiene citations se presenti
      citations: msg.metadata?.citations as
        | Array<{ chunk_id: string; score: number }>
        | undefined,
    }));

    if (isFirstLoad.current) {
      // Primo caricamento: sostituisci messaggi
      setMessages(chatMessages);
      isFirstLoad.current = false;
    } else {
      // Pagination: aggiungi solo nuovi messaggi (che non esistono già)
      setMessages((prevMessages) => {
        const existingIds = new Set(prevMessages.map((m) => m.id));
        const newMessages = chatMessages.filter((m) => !existingIds.has(m.id));
        
        if (newMessages.length > 0) {
          // Prepend nuovi messaggi storici (vanno prima degli esistenti)
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

  // Scroll listener per lazy loading pagination
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container || !hasMoreMessages) return;

    const handleScroll = () => {
      // Trigger load more quando scroll top < 100px (quasi al top)
      if (container.scrollTop < 100 && !isLoadingMore) {
        handleLoadMore();
      }
    };

    // Debounce scroll handler (300ms)
    let timeoutId: NodeJS.Timeout;
    const debouncedHandleScroll = () => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(handleScroll, 300);
    };

    container.addEventListener("scroll", debouncedHandleScroll);
    return () => {
      clearTimeout(timeoutId);
      container.removeEventListener("scroll", debouncedHandleScroll);
    };
  }, [hasMoreMessages, isLoadingMore, handleLoadMore]);

  // Auto-scroll al bottom quando arrivano nuovi messaggi
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = useCallback(
    async (question: string) => {
      setError(null);
      setLoading(true);

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: question,
      };
      setMessages((prev) => [...prev, userMsg]);

      try {
        const sendRes = await apiClient.sendMessage(sessionId, question);
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
    [sessionId]
  );

  return (
    <div className="flex flex-col h-screen">
      {/* Header - sticky per accesso dashboard durante scroll */}
      <div className="sticky top-0 z-10 flex-shrink-0 py-8 px-6 border-b bg-background">
        <div className="flex items-center justify-between max-w-[800px] mx-auto">
          <h1 className="text-3xl font-bold">Chat</h1>
          <div className="flex items-center gap-5">
            <div className="text-base font-medium opacity-70">
              Sessione:{" "}
              <span className="font-semibold">{sessionId || "-"}</span>
            </div>
            <HelpModal />
          </div>
        </div>
      </div>

      {/* Loading history indicator */}
      {isLoadingHistory && sessionId && (
        <div className="flex-shrink-0 px-4 pt-2">
          <div className="text-muted-foreground text-sm max-w-[800px] mx-auto flex items-center gap-2">
            <span className="animate-spin">⏳</span>
            Caricamento storico conversazione...
          </div>
        </div>
      )}

      {/* Error message - se presente */}
      {error && (
        <div className="flex-shrink-0 px-4 pt-2">
          <div
            role="alert"
            className="text-destructive max-w-[800px] mx-auto"
            data-testid="chat-error-message"
          >
            {error}
          </div>
        </div>
      )}

      {/* History error - graceful degradation (warning, non blocking) */}
      {historyError && (
        <div className="flex-shrink-0 px-4 pt-2">
          <div
            className="text-muted-foreground text-sm max-w-[800px] mx-auto"
            data-testid="history-warning"
          >
            ⚠️ Impossibile caricare lo storico precedente. Puoi continuare a usare
            la chat normalmente.
          </div>
        </div>
      )}

      {/* Chat messages - scroll area che cresce */}
      <div className="flex-1 p-4 flex flex-col">
        <div className="max-w-[800px] mx-auto w-full flex-1 flex flex-col">
          <div
            ref={messagesContainerRef}
            className="flex-1 rounded-lg border border-border bg-card p-3 text-card-foreground overflow-y-auto"
            data-testid="chat-messages-container"
          >
            {/* Load more indicator - in alto quando si scrolla verso top */}
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

      {/* Input - sticky bottom per accesso sempre disponibile */}
      <div className="sticky bottom-0 z-10 flex-shrink-0 p-4 border-t bg-background">
        <div className="max-w-[800px] mx-auto">
          <ChatInput onSubmit={handleSubmit} loading={loading} />
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
