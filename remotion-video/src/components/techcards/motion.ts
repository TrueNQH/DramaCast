import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

// Blur-in entrance used by every techcards element: fades in, rises 40px and un-blurs.
export const useBlurIn = (delayFrames = 0): React.CSSProperties => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - delayFrames, fps, config: { damping: 18, mass: 0.8 } });
  return {
    opacity: p,
    transform: `translateY(${interpolate(p, [0, 1], [40, 0])}px)`,
    filter: `blur(${interpolate(p, [0, 1], [14, 0])}px)`,
  };
};

// Pop-in for badges and buttons.
export const usePop = (delayFrames = 0): React.CSSProperties => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - delayFrames, fps, config: { damping: 9, stiffness: 160 } });
  return { opacity: Math.min(1, p * 1.5), transform: `scale(${interpolate(p, [0, 1], [0.6, 1])})` };
};

export const INK = "#1e1b4b";
export const INDIGO = "#4338ca";
export const BLUE = "#2563eb";
export const CYAN = "#0891b2";
