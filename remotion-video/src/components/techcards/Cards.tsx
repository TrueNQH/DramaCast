import { Heart, MessageCircle, Share2, ThumbsUp, Check, Send } from "lucide-react";
import {
  Img,
  interpolate,
  Loop,
  OffthreadVideo,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Card, Segment } from "../../types/schema";
import { BLUE, CYAN, INDIGO, INK, useBlurIn, usePop } from "./motion";

const BlurIn: React.FC<{ delay?: number; style?: React.CSSProperties; className?: string; children: React.ReactNode }> = ({
  delay = 0,
  style,
  className,
  children,
}) => (
  <div className={className} style={{ ...useBlurIn(delay), ...style }}>
    {children}
  </div>
);

const Pop: React.FC<{ delay?: number; children: React.ReactNode }> = ({ delay = 0, children }) => (
  <div style={{ ...usePop(delay), display: "inline-block" }}>{children}</div>
);

// Vertically centres a card in the space between the brand header and the source pill.
const Centered: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="absolute flex flex-col justify-center" style={{ left: 60, width: 960, top: 240, bottom: 250 }}>
    {children}
  </div>
);

const cardBox: React.CSSProperties = {
  background: "rgba(255,255,255,0.92)",
  borderRadius: 32,
  boxShadow: "0 24px 60px rgba(30,27,75,0.12)",
};

// "hero": kicker pill + huge stacked headline.
export const HeroCard: React.FC<{ card: Card }> = ({ card }) => {
  const words = card.headline.split(/\s+/).filter(Boolean);
  return (
    <div className="absolute left-0 right-0 flex flex-col items-center" style={{ top: 560, padding: "0 70px" }}>
      {card.kicker ? (
        <BlurIn delay={0}>
          <span
            className="flex items-center font-extrabold uppercase"
            style={{ ...cardBox, borderRadius: 999, padding: "14px 34px", gap: 16, fontSize: 32, letterSpacing: 2, color: INDIGO }}
          >
            <span style={{ width: 14, height: 14, borderRadius: 7, background: "linear-gradient(135deg,#ec4899,#6366f1)" }} />
            {card.kicker}
          </span>
        </BlurIn>
      ) : null}
      <div className="text-center uppercase" style={{ marginTop: 50, fontWeight: 900, fontSize: 150, lineHeight: 1.04, color: INK }}>
        {words.map((w, i) => (
          <BlurIn key={i} delay={6 + i * 4} style={{ display: "inline-block", margin: "0 18px" }}>
            {w}
          </BlurIn>
        ))}
      </div>
      <BlurIn delay={10 + words.length * 4}>
        <div style={{ width: 150, height: 12, borderRadius: 6, marginTop: 50, background: "linear-gradient(90deg,#ec4899,#6366f1)" }} />
      </BlurIn>
      {card.subline ? (
        <BlurIn delay={14 + words.length * 4}>
          <p className="text-center" style={{ fontSize: 44, color: "#6b7280", marginTop: 36 }}>
            {card.subline}
          </p>
        </BlurIn>
      ) : null}
    </div>
  );
};

const CardMedia: React.FC<{ segment: Segment }> = ({ segment }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = interpolate(frame, [0, segment.durationInFrames], [1.04, 1.14], { extrapolateRight: "clamp" });
  const style: React.CSSProperties = { width: "100%", height: "100%", objectFit: "cover", transform: `scale(${scale})` };
  if (!segment.mediaFile) {
    return <div style={{ width: "100%", height: "100%", background: "linear-gradient(135deg,#c7d2fe,#fbcfe8)" }} />;
  }
  if (segment.mediaType === "video") {
    return (
      <Loop durationInFrames={Math.max(1, Math.floor((segment.mediaDurationInSeconds ?? 9999) * fps))}>
        <OffthreadVideo src={staticFile(segment.mediaFile)} muted style={style} />
      </Loop>
    );
  }
  return <Img src={staticFile(segment.mediaFile)} style={style} />;
};

// "media": framed clip with a label chip, big gradient headline underneath.
export const MediaCard: React.FC<{ card: Card; segment: Segment; source: string }> = ({ card, segment, source }) => (
  <>
    <BlurIn delay={0} className="absolute" style={{ ...cardBox, left: 60, width: 960, top: 300, padding: 14 }}>
      <div className="relative overflow-hidden" style={{ height: 560, borderRadius: 22 }}>
        <CardMedia segment={segment} />
        {card.kicker ? (
          <span
            className="absolute font-semibold text-white"
            style={{ left: 22, bottom: 22, fontSize: 30, background: "rgba(15,23,42,0.85)", borderRadius: 14, padding: "8px 20px" }}
          >
            {card.kicker}
          </span>
        ) : null}
      </div>
    </BlurIn>
    {source ? (
      <BlurIn delay={6} className="absolute left-0 right-0 text-center" style={{ top: 912, fontSize: 28, color: "#9ca3af" }}>
        Nguồn: {source}
      </BlurIn>
    ) : null}
    <div className="absolute left-0 right-0 text-center" style={{ top: 1000, padding: "0 60px" }}>
      <BlurIn delay={10}>
        <span
          style={{
            fontSize: 124,
            fontWeight: 800,
            lineHeight: 1.08,
            background: "linear-gradient(90deg,#2563eb,#4f46e5)",
            WebkitBackgroundClip: "text",
            color: "transparent",
          }}
        >
          {card.headline}
        </span>
      </BlurIn>
      {card.subline ? (
        <BlurIn delay={18} style={{ marginTop: 34, padding: "0 30px", fontSize: 46, color: "#6b7280" }}>
          {card.subline}
        </BlurIn>
      ) : null}
    </div>
  </>
);

// "bullets": titled card, items revealed one by one across the segment.
export const BulletsCard: React.FC<{ card: Card; segment: Segment }> = ({ card, segment }) => {
  const step = Math.max(8, Math.floor((segment.durationInFrames * 0.6) / Math.max(1, card.items.length)));
  return (
    <Centered>
      <BlurIn delay={0} style={{ ...cardBox, padding: "56px 60px", border: "3px solid #c7d2fe" }}>
        <p className="font-extrabold" style={{ fontSize: 72, color: INDIGO, fontStyle: "italic" }}>
          {card.headline}
        </p>
        <div style={{ height: 3, background: "#e0e7ff", margin: "30px 0 34px" }} />
        {card.items.map((item, i) => (
          <BlurIn key={i} delay={10 + i * step} className="flex items-start" style={{ gap: 26, marginBottom: 30 }}>
            <span style={{ width: 22, height: 22, borderRadius: 11, background: "#3b82f6", marginTop: 24, flexShrink: 0 }} />
            <span style={{ fontSize: 54, lineHeight: 1.3, color: "#1f2937" }}>{item}</span>
          </BlurIn>
        ))}
      </BlurIn>
    </Centered>
  );
};

const VersusSide: React.FC<{ label: string; text: string; color: string; border: string; winner: boolean; delay: number; top: number; winnerDelay: number }> = ({
  label,
  text,
  color,
  border,
  winner,
  delay,
  top,
  winnerDelay,
}) => (
  <BlurIn delay={delay} className="absolute" style={{ ...cardBox, left: 60, width: 960, top, padding: "44px 54px", border: `3px solid ${border}` }}>
    <p className="font-semibold uppercase" style={{ fontSize: 32, letterSpacing: 4, color: "#6b7280" }}>
      {label}
    </p>
    <p className="font-extrabold" style={{ fontSize: 86, lineHeight: 1.1, color, marginTop: 12 }}>
      {text}
    </p>
    {winner ? (
      <div style={{ marginTop: 22 }}>
        <Pop delay={winnerDelay}>
          <span
            className="font-extrabold"
            style={{ fontSize: 28, letterSpacing: 3, color: "#0369a1", background: "#e0f2fe", border: "2px solid #bae6fd", borderRadius: 12, padding: "6px 18px" }}
          >
            WINNER
          </span>
        </Pop>
      </div>
    ) : null}
  </BlurIn>
);

// "versus": two stacked sides with a "vs" between and a WINNER badge.
export const VersusCard: React.FC<{ card: Card; segment: Segment }> = ({ card, segment }) => {
  const v = card.versus ?? { leftLabel: "", leftText: card.headline, rightLabel: "", rightText: card.subline, winner: "" as const };
  const half = Math.floor(segment.durationInFrames * 0.35);
  return (
    <>
      <VersusSide label={v.leftLabel} text={v.leftText} color={INDIGO} border="#a5b4fc" winner={v.winner === "left"} delay={0} top={400} winnerDelay={half * 2} />
      <BlurIn delay={half / 2} className="absolute left-0 right-0 text-center font-extrabold" style={{ top: 830, fontSize: 96, color: "#cbd5e1" }}>
        vs
      </BlurIn>
      <VersusSide label={v.rightLabel} text={v.rightText} color={CYAN} border="#67e8f9" winner={v.winner === "right"} delay={half} top={980} winnerDelay={half * 2} />
    </>
  );
};

// "quote": a post or comment pulled from the source.
export const QuoteCard: React.FC<{ card: Card; segment: Segment }> = ({ card, segment }) => (
  <Centered>
    <BlurIn delay={0} style={{ ...cardBox, padding: "50px 56px" }}>
      <div className="flex items-center" style={{ gap: 24 }}>
        <div
          className="flex items-center justify-center rounded-full text-white font-extrabold"
          style={{ width: 92, height: 92, fontSize: 42, background: "linear-gradient(135deg,#6366f1,#ec4899)" }}
        >
          {(segment.authorName || "?").replace(/^[@u/]+/, "").charAt(0).toUpperCase()}
        </div>
        <div>
          <p className="font-bold" style={{ fontSize: 40, color: "#111827" }}>
            {segment.authorName || "Cư dân mạng"}
          </p>
          <p style={{ fontSize: 30, color: "#9ca3af" }}>{card.kicker || segment.platform}</p>
        </div>
      </div>
      <p style={{ fontSize: 58, lineHeight: 1.32, color: INK, margin: "34px 0 30px" }}>“{card.headline}”</p>
      {segment.likesCount ? (
        <span className="flex items-center font-semibold" style={{ gap: 12, fontSize: 34, color: "#e11d48" }}>
          <Heart size={40} fill="currentColor" />
          {segment.likesCount}
        </span>
      ) : null}
    </BlurIn>
  </Centered>
);

const FloatingReactions: React.FC = () => {
  const frame = useCurrentFrame();
  const icons = [Heart, ThumbsUp, Heart, ThumbsUp, Heart, Heart];
  return (
    <>
      {icons.map((Icon, i) => {
        const t = frame - 20 - i * 9;
        if (t < 0) return null;
        const y = interpolate(t, [0, 60], [0, -360], { extrapolateRight: "clamp" });
        const o = interpolate(t, [0, 8, 45, 60], [0, 1, 1, 0], { extrapolateRight: "clamp" });
        const red = Icon === Heart;
        return (
          <div
            key={i}
            className="absolute flex items-center justify-center rounded-full text-white"
            style={{
              right: 120 + (i % 3) * 34,
              top: 960 + y,
              width: 74,
              height: 74,
              opacity: o,
              background: red ? "#f43f5e" : BLUE,
              boxShadow: "0 8px 20px rgba(0,0,0,0.15)",
            }}
          >
            <Icon size={40} fill="currentColor" />
          </div>
        );
      })}
    </>
  );
};

// "cta": follow-the-channel card with an animated follow button, plus the closing question.
export const CtaCard: React.FC<{ card: Card; segment: Segment; brandName: string; brandColor: string }> = ({
  card,
  segment,
  brandName,
  brandColor,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const clickAt = Math.floor(segment.durationInFrames * 0.35);
  const followed = frame >= clickAt;
  const press = spring({ frame: frame - clickAt, fps, config: { damping: 10 } });
  const handle = brandName.toLowerCase().replace(/\s+/g, "");
  return (
    <>
      <BlurIn delay={0} className="absolute left-0 right-0 flex justify-center" style={{ top: 420 }}>
        <span className="font-bold text-white" style={{ fontSize: 36, background: BLUE, borderRadius: 999, padding: "14px 38px" }}>
          {card.kicker || "Theo dõi để hóng drama mỗi ngày"}
        </span>
      </BlurIn>
      <BlurIn delay={6} className="absolute overflow-hidden" style={{ ...cardBox, left: 110, width: 860, top: 530 }}>
        <div style={{ height: 190, background: `linear-gradient(120deg, ${brandColor}, #6366f1)` }} />
        <div className="flex flex-col items-center" style={{ marginTop: -95, padding: "0 50px 30px" }}>
          <div
            className="flex items-center justify-center rounded-full bg-white font-extrabold"
            style={{ width: 190, height: 190, border: "8px solid white", boxShadow: "0 10px 30px rgba(0,0,0,0.12)", fontSize: 90, color: brandColor }}
          >
            {brandName.charAt(0)}
          </div>
          <p className="font-extrabold" style={{ fontSize: 62, color: "#111827", marginTop: 18 }}>
            {brandName}
          </p>
          <p className="font-semibold" style={{ fontSize: 34, color: BLUE }}>
            @{handle}
          </p>
          <div className="flex" style={{ gap: 22, marginTop: 34, width: "100%" }}>
            <div
              className="flex flex-1 items-center justify-center font-bold"
              style={{
                fontSize: 36,
                gap: 12,
                height: 92,
                borderRadius: 18,
                background: followed ? "#e0e7ff" : BLUE,
                color: followed ? INDIGO : "white",
                transform: `scale(${followed ? 0.94 + 0.06 * press : 1})`,
              }}
            >
              {followed ? <Check size={40} /> : null}
              {followed ? "Đã theo dõi" : "Theo dõi"}
            </div>
            <div className="flex flex-1 items-center justify-center font-bold" style={{ fontSize: 36, gap: 12, height: 92, borderRadius: 18, background: "#e5e7eb", color: "#111827" }}>
              <Send size={36} />
              Nhắn tin
            </div>
          </div>
          <div className="flex justify-around" style={{ width: "100%", marginTop: 30, paddingTop: 24, borderTop: "2px solid #e5e7eb", fontSize: 32, color: "#4b5563" }}>
            <span className="flex items-center" style={{ gap: 10, color: BLUE }}>
              <ThumbsUp size={36} /> Thích
            </span>
            <span className="flex items-center" style={{ gap: 10 }}>
              <MessageCircle size={36} /> Bình luận
            </span>
            <span className="flex items-center" style={{ gap: 10 }}>
              <Share2 size={36} /> Chia sẻ
            </span>
          </div>
        </div>
      </BlurIn>
      <FloatingReactions />
      {card.headline ? (
        <BlurIn delay={14} className="absolute left-0 right-0 text-center font-extrabold" style={{ top: 1440, padding: "0 80px", fontSize: 58, lineHeight: 1.25, color: INK }}>
          {card.headline}
        </BlurIn>
      ) : null}
    </>
  );
};
