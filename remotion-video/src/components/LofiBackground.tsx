import { AbsoluteFill, Loop, OffthreadVideo, staticFile, useVideoConfig } from "remotion";

// Loopable background clip with blur + dark vignette so cards and subtitles stay readable.
export const LofiBackground: React.FC<{ file: string }> = ({ file }) => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill>
      {file ? (
        <Loop durationInFrames={fps * 10}>
          <OffthreadVideo
            src={staticFile(file)}
            muted
            style={{ width: "100%", height: "100%", objectFit: "cover", filter: "blur(6px) brightness(0.7)", transform: "scale(1.08)" }}
          />
        </Loop>
      ) : (
        <AbsoluteFill className="bg-gradient-to-b from-slate-800 to-slate-950" />
      )}
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, transparent 35%, rgba(0,0,0,0.75) 100%)" }} />
    </AbsoluteFill>
  );
};
