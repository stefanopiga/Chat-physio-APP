import React from "react";

type Props = {
  id: string;
  excerpt?: string | null;
  onClick?: () => void;
  "data-testid"?: string;
};

const CitationBadge: React.FC<Props> = ({ id, excerpt, onClick, "data-testid": testId }) => {
  return (
    <button
      type="button"
      aria-label={`Fonte ${id}`}
      aria-haspopup="dialog"
      title={excerpt || id}
      onClick={onClick}
      data-testid={testId}
      className="cursor-pointer rounded border border-border bg-background px-1.5 py-0.5 text-[12px] shadow-sm hover:bg-accent hover:text-accent-foreground"
    >
      {id}
    </button>
  );
};

export default CitationBadge;
