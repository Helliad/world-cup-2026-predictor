import { type ReactNode, useEffect, useRef, useState } from "react";

// Scroll-reveal wrapper: the element starts hidden (see `.reveal` in index.css)
// and eases in the first time it scrolls into view. One-shot (it never hides
// again). Under prefers-reduced-motion the CSS shows it immediately, so this is
// purely additive polish, never a content gate.
export function Reveal({
  children,
  className = "",
  delay = 0,
  threshold = 0.15,
}: {
  children: ReactNode;
  className?: string;
  delay?: number; // ms, staggers siblings
  threshold?: number;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    // Already in view on mount (above the fold) → show without waiting.
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setShown(true);
          io.disconnect();
        }
      },
      { threshold, rootMargin: "0px 0px -8% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [threshold]);

  return (
    <div
      ref={ref}
      className={`reveal ${shown ? "reveal-in" : ""} ${className}`}
      style={delay ? { transitionDelay: `${delay}ms` } : undefined}
    >
      {children}
    </div>
  );
}

// Count a number up from 0 the first time it scrolls into view. Falls back to
// the final value instantly under reduced motion (or if the observer never
// fires). `format` controls rendering (e.g. "100k", "48").
export function CountUp({
  to,
  duration = 1200,
  format = (n: number) => Math.round(n).toString(),
  className = "",
}: {
  to: number;
  duration?: number;
  format?: (n: number) => string;
  className?: string;
}) {
  const ref = useRef<HTMLSpanElement | null>(null);
  const [value, setValue] = useState(0);
  const started = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setValue(to);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (!entries.some((e) => e.isIntersecting) || started.current) return;
        started.current = true;
        io.disconnect();
        let raf = 0;
        // performance.now is allowed in the browser; only Date.now is restricted
        // in workflow scripts, not in app code.
        const start = performance.now();
        const tick = (now: number) => {
          const t = Math.min(1, (now - start) / duration);
          const eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
          setValue(to * eased);
          if (t < 1) raf = requestAnimationFrame(tick);
        };
        raf = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(raf);
      },
      { threshold: 0.5 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [to, duration]);

  return (
    <span ref={ref} className={className}>
      {format(value)}
    </span>
  );
}
