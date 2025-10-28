import React, { useState } from "react";
import apiClient from "../lib/apiClient";
import CitationBadge from "./CitationBadge";
import CitationPopover from "./CitationPopover";
import FeedbackControls from "./FeedbackControls";
import LoadingIndicator from "./LoadingIndicator";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  messageId?: string;
  citations?: Array<{
    chunk_id: string;
    document_id?: string | null;
    excerpt?: string | null;
    position?: number | null;
  }>;
};

type Props = {
  messages: ChatMessage[];
  loading?: boolean;
};

const ChatMessagesList: React.FC<Props> = ({ messages, loading = false }) => {
  const [pendingFeedback, setPendingFeedback] = useState<string | null>(null);
  const [openCitation, setOpenCitation] = useState<string | null>(null);

  async function handleVote(
    sessionId: string,
    messageId: string,
    vote: "up" | "down"
  ) {
    try {
      setPendingFeedback(messageId);
      // Garantisce che il render del bottone disabilitato avvenga prima della risposta
      await new Promise((resolve) => setTimeout(resolve, 0));
      await apiClient.sendFeedback(sessionId, messageId, vote);
    } finally {
      // Mantiene lo stato disabilitato brevemente per UX/test stability
      setTimeout(() => setPendingFeedback(null), 200);
    }
  }

  return (
    <div className="flex flex-col gap-2" data-testid="chat-messages-list">
      {messages.map((m) => (
        <div
          key={m.id}
          data-testid={`chat-message-${m.role}`}
          className={
            (m.role === "user"
              ? "self-end bg-primary/10"
              : "self-start bg-muted") + " max-w-[75%] rounded-md p-2"
          }
        >
          <div className="text-[12px] opacity-70">{m.role}</div>
          <div data-testid="message-content">{m.content}</div>
          {m.role === "assistant" && m.citations && m.citations.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1.5 relative" data-testid="message-citations">
              {m.citations.map((c) => (
                <div key={c.chunk_id} className="relative">
                  <CitationBadge
                    id={c.chunk_id}
                    excerpt={c.excerpt}
                    data-testid={`citation-badge-${c.chunk_id}`}
                    onClick={() =>
                      setOpenCitation(
                        openCitation === c.chunk_id ? null : c.chunk_id
                      )
                    }
                  />
                  {openCitation === c.chunk_id && (
                    <div className="absolute left-0 -bottom-7">
                      <CitationPopover
                        excerpt={c.excerpt}
                        documentId={c.document_id || null}
                        position={c.position || null}
                        onRequestClose={() => setOpenCitation(null)}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
          {m.role === "assistant" && m.messageId && (
            <div className="mt-1.5">
              <FeedbackControls
                disabled={pendingFeedback === m.messageId}
                onUp={() =>
                  handleVote(
                    localStorage.getItem("chat.sessionId") || "",
                    m.messageId!,
                    "up"
                  )
                }
                onDown={() =>
                  handleVote(
                    localStorage.getItem("chat.sessionId") || "",
                    m.messageId!,
                    "down"
                  )
                }
              />
            </div>
          )}
        </div>
      ))}
      
      {/* Loading indicator in-chat */}
      {loading && <LoadingIndicator />}
    </div>
  );
};

export default ChatMessagesList;
