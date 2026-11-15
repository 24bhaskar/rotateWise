import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { GLOSSARY } from "../content/glossary";

/** A jargon word with a plain-language definition on hover, focus or tap. */
export function Term({ k, children }: { k: keyof typeof GLOSSARY | string; children?: ReactNode }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", close); };
  }, [open]);
  const def = GLOSSARY[k];
  if (!def) return <>{children ?? k}</>;
  return (
    <span ref={ref} style={{ position: "relative" }} onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button type="button" className="term" aria-describedby={open ? id : undefined} aria-expanded={open}
              onClick={() => setOpen((o) => !o)} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}>
        {children ?? k}
      </button>
      {open && <span role="tooltip" id={id} className="term-pop">{def}</span>}
    </span>
  );
}
