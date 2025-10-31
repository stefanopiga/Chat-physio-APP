import React, { useState, useRef, useEffect } from "react";
import { Textarea } from "@/components/ui/textarea";

type Props = {
  onSubmit: (question: string) => Promise<void> | void;
  loading?: boolean;
};

const ChatInput: React.FC<Props> = ({ onSubmit, loading }) => {
  const [question, setQuestion] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize logic - CRITICAL: reset height BEFORE calculating scrollHeight
  const adjustHeight = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = "auto"; // ⚠️ RESET FIRST - prevents resize loops
    const scrollHeight = textarea.scrollHeight;
    const maxHeight = 96; // 4 righe * ~24px = 96px

    textarea.style.height = `${Math.min(scrollHeight, maxHeight)}px`;
  };

  useEffect(() => {
    adjustHeight();
  }, [question]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;
    await onSubmit(q);
    setQuestion("");
    // Reset height after submit
    setTimeout(() => adjustHeight(), 0);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault(); // ← CRITICAL: prevent default newline
      void handleSubmit(e as unknown as React.FormEvent);
    }
    // Shift+Enter: default behavior (newline)
  };

  const isDisabled = !!loading || question.trim().length === 0;

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-end gap-2"
      data-testid="chat-input-form"
    >
      <Textarea
        ref={textareaRef}
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Inserisci la tua domanda..."
        disabled={!!loading}
        rows={1}
        data-testid="chat-input-field"
        className="resize-none overflow-y-auto max-h-24"
      />
      <button
        type="submit"
        disabled={isDisabled}
        data-testid="chat-submit-button"
        className="inline-flex items-center justify-center whitespace-nowrap rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50 self-end"
      >
        {loading ? "Invio..." : "Invia"}
      </button>
    </form>
  );
};

export default ChatInput;
