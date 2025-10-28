import React, { useEffect, useRef } from "react";

type Props = {
  excerpt?: string | null;
  documentId?: string | null;
  position?: number | null;
  onRequestClose: () => void;
};

const CitationPopover: React.FC<Props> = ({
  excerpt,
  documentId,
  position,
  onRequestClose,
}) => {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onRequestClose();
    }
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node))
        onRequestClose();
    }
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onClickOutside);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onClickOutside);
    };
  }, [onRequestClose]);

  return (
    <div
      ref={ref}
      role="tooltip"
      aria-live="polite"
      data-testid="citation-popover"
      className="absolute z-[1000] max-w-80 rounded-md border border-border bg-popover p-2 text-popover-foreground shadow-lg pointer-events-none"
    >
      <div
        className="mb-1 text-[12px] text-muted-foreground"
        data-testid="popover-document-id"
      >
        Documento: {documentId || "-"}{" "}
        {typeof position === "number" ? `(pos ${position})` : ""}
      </div>
      <div className="text-[13px]" data-testid="popover-excerpt">
        {excerpt || "(nessun estratto)"}
      </div>
    </div>
  );
};

export default CitationPopover;
