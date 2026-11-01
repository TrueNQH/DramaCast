import { AbsoluteFill, Img, interpolate, Loop, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Segment } from "../../types/schema";

// Stock photo/clip with a slow Ken Burns move. Alternates zoom-in / zoom-out per segment.
export const BrollMedia: React.FC<{ segment: Segment }> = ({ segment }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const zoomIn = segment.id % 2 === 1;
  const progress = interpolate(frame, [0, segment.durationInFrames || durationInFrames], [0, 1], {
    extrapolateRight: "clamp",
  });
  const scale = zoomIn ? 1 + 0.12 * progress : 1.12 - 0.12 * progress;
  const panX = (zoomIn ? -1 : 1) * 20 * progress;
  const style: React.CSSProperties = {
    width: "100%",
    height: "100%",
    objectFit: "cover",
    transform: `scale(${scale}) translateX(${panX}px)`,
  };

  if (!segment.mediaFile) {
    return <AbsoluteFill style={{ background: "linear-gradient(160deg, #3a3a3a, #111)" }} />;
  }

  if (segment.mediaType === "video") {
    const clipFrames = Math.max(1, Math.floor((segment.mediaDurationInSeconds ?? 9999) * fps));
    return (
      <AbsoluteFill>
        <Loop durationInFrames={clipFrames}>
          <OffthreadVideo src={staticFile(segment.mediaFile)} muted style={style} />
        </Loop>
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill>
      <Img src={staticFile(segment.mediaFile)} style={style} />
    </AbsoluteFill>
  );
};
