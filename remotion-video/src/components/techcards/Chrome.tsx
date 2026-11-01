import { AbsoluteFill, useCurrentFrame } from "remotion";
import { BLUE } from "./motion";

// Soft pastel backdrop with three slowly drifting colour blobs.
export const PastelBackground: React.FC = () => {
  const t = useCurrentFrame() / 30;
  const blob = (x: number, y: number, size: number, color: string): React.CSSProperties => ({
    position: "absolute",
    left: x,
    top: y,
    width: size,
    height: size,
    borderRadius: "50%",
    background: color,
    filter: "blur(120px)",
    opacity: 0.75,
  });
  return (
    <AbsoluteFill style={{ background: "#f6f4fb" }}>
      <div style={blob(560 + 60 * Math.sin(t / 3), -160 + 40 * Math.cos(t / 4), 760, "#d8d0ff")} />
      <div style={blob(-260 + 50 * Math.cos(t / 5), 760 + 60 * Math.sin(t / 3), 700, "#ffd9ec")} />
      <div style={blob(-120 + 40 * Math.sin(t / 4), 1500 + 30 * Math.cos(t / 3), 780, "#cdeff6")} />
    </AbsoluteFill>
  );
};

// Channel logo + name, top-left, on every scene.
export const BrandHeader: React.FC<{ name: string; color: string }> = ({ name, color }) => (
  <div className="absolute flex items-center" style={{ top: 96, left: 64, gap: 24 }}>
    <div
      className="flex items-center justify-center bg-white font-extrabold"
      style={{ width: 96, height: 96, borderRadius: 24, boxShadow: "0 8px 24px rgba(30,27,75,0.12)", fontSize: 46, color }}
    >
      {name.charAt(0)}
    </div>
    <span className="font-bold" style={{ fontSize: 42, color: "#111827" }}>
      {name}
    </span>
  </div>
);

// Source pill at the bottom ("threads.net").
export const SourcePill: React.FC<{ label: string }> = ({ label }) =>
  label ? (
    <div className="absolute left-0 right-0 flex justify-center" style={{ top: 1730 }}>
      <span
        className="font-semibold"
        style={{
          fontSize: 32,
          color: BLUE,
          background: "rgba(219,234,254,0.85)",
          border: "2px solid #bfdbfe",
          borderRadius: 999,
          padding: "10px 34px",
        }}
      >
        {label}
      </span>
    </div>
  ) : null;
