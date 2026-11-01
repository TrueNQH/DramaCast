import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

type Props = {
  title: string;
  highlight: string;
  brandName: string;
  brandColor: string;
};

const splitHighlight = (title: string, highlight: string): [string, string, string] => {
  const at = highlight ? title.indexOf(highlight) : -1;
  if (at < 0) return [title, "", ""];
  return [title.slice(0, at), highlight, title.slice(at + highlight.length)];
};

// Opening hook: white headline card with an offset brand-colored layer behind it.
export const TitleCard: React.FC<Props> = ({ title, highlight, brandName, brandColor }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 14 } });
  const translateY = interpolate(enter, [0, 1], [60, 0]);
  const [before, marked, after] = splitHighlight(title, highlight);

  return (
    <div
      className="absolute"
      style={{ top: 1010, left: 110, width: 840, opacity: enter, transform: `translateY(${translateY}px)` }}
    >
      <div
        className="absolute rounded-2xl"
        style={{ inset: 0, transform: "translate(16px, 14px)", background: brandColor, border: "3px solid rgba(0,0,0,0.35)" }}
      />
      <div className="relative rounded-2xl bg-white px-12 pt-10 pb-12" style={{ border: "3px solid rgba(0,0,0,0.25)" }}>
        <div className="flex items-center justify-between mb-8">
          <span className="font-extrabold tracking-widest" style={{ color: brandColor, fontSize: 30 }}>
            {brandName}
          </span>
          <span className="rounded-sm" style={{ width: 120, height: 18, background: brandColor }} />
        </div>
        <p className="font-bold text-slate-900" style={{ fontSize: 48, lineHeight: 1.25 }}>
          {before}
          <span style={{ color: brandColor }}>{marked}</span>
          {after}
        </p>
        <svg width="70" height="14" viewBox="0 0 70 14" className="mt-10">
          <path d="M2 7 Q 10 1 18 7 T 34 7 T 50 7 T 68 7" fill="none" stroke={brandColor} strokeWidth="3" strokeLinecap="round" />
        </svg>
      </div>
    </div>
  );
};
