import { useCurrentFrame, useVideoConfig } from "remotion";
import { Subtitle } from "../types/schema";

// Returns the subtitle whose start has passed most recently; it stays on screen through pauses.
export const activeSubtitleIndex = (subtitles: Subtitle[], ms: number): number => {
  let index = -1;
  subtitles.forEach((s, i) => {
    if (s.startMs <= ms) index = i;
  });
  return index;
};

// Karaoke line for the social template: words light up as they are spoken.
export const SubtitleTrack: React.FC<{ subtitles: Subtitle[] }> = ({ subtitles }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ms = (frame / fps) * 1000;
  const current = activeSubtitleIndex(subtitles, ms);
  if (current < 0) return null;

  // Show a window of ~8 words around the current one.
  const windowStart = Math.floor(current / 8) * 8;
  const words = subtitles.slice(windowStart, windowStart + 8);

  return (
    <div className="absolute left-0 right-0 flex justify-center px-16" style={{ top: 1380 }}>
      <p className="text-center text-5xl font-extrabold leading-tight" style={{ textShadow: "0 4px 18px rgba(0,0,0,0.8)" }}>
        {words.map((w, i) => (
          <span key={windowStart + i} className={windowStart + i <= current ? "text-amber-300" : "text-white/70"}>
            {w.text}{" "}
          </span>
        ))}
      </p>
    </div>
  );
};
