import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Subtitle } from "../../types/schema";

export type Paragraph = { text: string; subtitles: Subtitle[]; current: boolean };

// Dark text panel: earlier paragraphs of the page stay, the current one appears phrase by phrase
// as it is spoken. Unspoken phrases keep their space (transparent) so the box does not jump.
export const StoryTextBox: React.FC<{ paragraphs: Paragraph[] }> = ({ paragraphs }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ms = (frame / fps) * 1000;

  return (
    <div
      className="absolute rounded-2xl text-white"
      style={{
        left: 60,
        width: 960,
        top: 330,
        padding: "44px 50px 14px",
        background: "rgba(24,24,28,0.9)",
        boxShadow: "0 30px 80px rgba(0,0,0,0.45)",
      }}
    >
      {paragraphs.map((p, i) => (
        <p key={i} className="font-semibold" style={{ fontSize: 46, lineHeight: 1.42, marginBottom: 32 }}>
          {p.current && p.subtitles.length
            ? p.subtitles.map((s, k) => {
                const shown = interpolate(ms - s.startMs, [0, 140], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
                return (
                  <span key={k} style={{ opacity: shown }}>
                    {s.text}{" "}
                  </span>
                );
              })
            : p.text}
        </p>
      ))}
    </div>
  );
};
