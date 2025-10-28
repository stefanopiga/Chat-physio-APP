import React from "react";

const LoadingIndicator: React.FC = () => {
  return (
    <div
      className="self-start bg-muted max-w-[75%] rounded-md p-2"
      role="status"
      aria-live="polite"
      aria-label="L'assistente sta preparando la risposta"
      data-testid="loading-indicator"
    >
      <div className="text-[12px] opacity-70">assistant</div>
      <div className="flex items-center gap-2">
        <span className="text-sm">L'assistente sta pensando</span>
        <span className="flex gap-1">
          <span className="animate-bounce" style={{ animationDelay: "0ms" }}>.</span>
          <span className="animate-bounce" style={{ animationDelay: "100ms" }}>.</span>
          <span className="animate-bounce" style={{ animationDelay: "200ms" }}>.</span>
        </span>
      </div>
    </div>
  );
};

export default LoadingIndicator;

