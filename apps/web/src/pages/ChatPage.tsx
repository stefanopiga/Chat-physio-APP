import React, { useCallback, useEffect, useState, useRef } from "react";
import apiClient from "../lib/apiClient";
import ChatInput from "../components/ChatInput";
import ChatMessagesList, {
  type ChatMessage,
} from "../components/ChatMessagesList";
import HelpModal from "../components/HelpModal";

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
  const [sessionId, setSessionId] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSessionId(getOrCreateSessionId());
  }, []);

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
      {/* Header - fisso in alto */}
      <div className="flex-shrink-0 py-8 px-6 border-b">
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

      {/* Chat messages - scroll area che cresce */}
      <div className="flex-1 p-4 flex flex-col">
        <div className="max-w-[800px] mx-auto w-full flex-1 flex flex-col">
          <div
            className="flex-1 rounded-lg border border-border bg-card p-3 text-card-foreground overflow-y-auto"
            data-testid="chat-messages-container"
          >
            <ChatMessagesList messages={messages} loading={loading} />
            <div ref={messagesEndRef} />
          </div>
        </div>
      </div>

      {/* Input - fisso in basso */}
      <div className="flex-shrink-0 p-4 border-t bg-background">
        <div className="max-w-[800px] mx-auto">
          <ChatInput onSubmit={handleSubmit} loading={loading} />
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
