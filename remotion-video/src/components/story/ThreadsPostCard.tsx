import { Heart, MessageCircle, MoreHorizontal, Repeat2, Send } from "lucide-react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

type Props = { username: string; community: string; likes: string; text: string };

// Threads-style post that opens the story (white card, avatar, "› community", action row).
export const ThreadsPostCard: React.FC<Props> = ({ username, community, likes, text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 15 } });
  const name = username.replace(/^@/, "") || "an_danh";

  return (
    <div
      className="absolute bg-white rounded-2xl shadow-2xl"
      style={{
        left: 60,
        width: 960,
        top: 640,
        padding: "36px 40px 30px",
        opacity: enter,
        transform: `translateY(${interpolate(enter, [0, 1], [70, 0])}px) scale(${0.96 + enter * 0.04})`,
      }}
    >
      <div className="flex items-center" style={{ gap: 22 }}>
        <div
          className="flex items-center justify-center rounded-full text-white font-extrabold"
          style={{ width: 88, height: 88, fontSize: 40, background: "linear-gradient(135deg,#f58529,#dd2a7b,#8134af)" }}
        >
          {name.charAt(0).toUpperCase()}
        </div>
        <div className="flex-1 flex items-baseline" style={{ gap: 14, fontSize: 38 }}>
          <span className="font-bold text-black">{name}</span>
          {community ? <span className="text-neutral-500">› {community}</span> : null}
          <span className="text-neutral-400" style={{ fontSize: 32 }}>1 ngày</span>
        </div>
        <MoreHorizontal size={44} className="text-neutral-400" />
      </div>
      <p className="text-black" style={{ fontSize: 48, lineHeight: 1.35, margin: "26px 0 28px" }}>
        {text}
      </p>
      <div className="flex items-center text-neutral-500" style={{ gap: 44, fontSize: 32 }}>
        <span className="flex items-center" style={{ gap: 10 }}>
          <Heart size={40} />
          {likes}
        </span>
        <MessageCircle size={40} />
        <Repeat2 size={40} />
        <Send size={40} />
      </div>
    </div>
  );
};
