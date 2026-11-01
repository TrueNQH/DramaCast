import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Subtitle } from "../../types/schema";
import { activeSubtitleIndex } from "../SubtitleTrack";

// Phrase-level caption centered in the brand-colored lower panel.
export const NewsSubtitle: React.FC<{ subtitles: Subtitle[]; top: number }> = ({ subtitles, top }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ms = (frame / fps) * 1000;
  const index = activeSubtitleIndex(subtitles, ms);
  if (index < 0) return null;

  const current = subtitles[index];
  const sinceStart = ms - current.startMs;
  const opacity = interpolate(sinceStart, [0, 120], [0, 1], { extrapolateRight: "clamp" });
  const translateY = interpolate(sinceStart, [0, 160], [10, 0], { extrapolateRight: "clamp" });

  return (
    <div className="absolute left-0 right-0 flex justify-center" style={{ top }}>
      <p
        className="text-center text-white font-bold"
        style={{
          width: 720,
          fontSize: 36,
          lineHeight: 1.35,
          opacity,
          transform: `translateY(${translateY}px)`,
          textShadow: "0 2px 8px rgba(0,0,0,0.35)",
        }}
      >
        {current.text}
      </p>
    </div>
  );
};
