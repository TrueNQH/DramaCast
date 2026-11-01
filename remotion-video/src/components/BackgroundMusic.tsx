import { Audio, interpolate, staticFile, useVideoConfig } from "remotion";

// Looping BGM under the narration, faded in over the first second and out over the last 1.5s.
export const BackgroundMusic: React.FC<{ file: string; volume: number }> = ({ file, volume }) => {
  const { fps, durationInFrames } = useVideoConfig();
  if (!file) return null;
  const fadeIn = fps;
  const fadeOut = Math.round(fps * 1.5);
  return (
    <Audio
      src={staticFile(file)}
      loop
      volume={(f) =>
        interpolate(f, [0, fadeIn, Math.max(fadeIn + 1, durationInFrames - fadeOut), durationInFrames], [0, volume, volume, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      }
    />
  );
};
