import React, { memo } from "react";

type Props = {
  disabled?: boolean;
  onUp: () => void;
  onDown: () => void;
};

const FeedbackControls: React.FC<Props> = memo(({ disabled, onUp, onDown }) => {
  return (
    <div className="flex gap-2">
      <button
        type="button"
        aria-label="Vota positivo"
        disabled={disabled}
        onClick={onUp}
        className="rounded border border-border bg-background px-2 py-1 text-foreground shadow-sm hover:bg-accent hover:text-accent-foreground disabled:cursor-not-allowed disabled:opacity-50"
      >
        👍
      </button>
      <button
        type="button"
        aria-label="Vota negativo"
        disabled={disabled}
        onClick={onDown}
        className="rounded border border-border bg-background px-2 py-1 text-foreground shadow-sm hover:bg-accent hover:text-accent-foreground disabled:cursor-not-allowed disabled:opacity-50"
      >
        👎
      </button>
    </div>
  );
});

FeedbackControls.displayName = "FeedbackControls";

export default FeedbackControls;
