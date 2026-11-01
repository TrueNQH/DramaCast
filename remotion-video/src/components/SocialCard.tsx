import { BadgeCheck, Heart, MessageCircle, Quote, Twitter, Youtube } from "lucide-react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Segment } from "../types/schema";

const PLATFORM_LABEL: Record<Segment["platform"], string> = {
  twitter: "X / Twitter",
  reddit: "Reddit",
  xiaohongshu: "Xiaohongshu",
  youtube: "YouTube",
  narrator: "Người dẫn chuyện",
};

const PlatformIcon: React.FC<{ platform: Segment["platform"] }> = ({ platform }) => {
  const props = { size: 40, strokeWidth: 2.2 };
  if (platform === "twitter") return <Twitter {...props} />;
  if (platform === "youtube") return <Youtube {...props} />;
  if (platform === "narrator") return <Quote {...props} />;
  return <MessageCircle {...props} />;
};

export const SocialCard: React.FC<{ segment: Segment }> = ({ segment }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 14 } });
  const translateY = interpolate(enter, [0, 1], [80, 0]);

  return (
    <div className="absolute left-0 right-0 flex justify-center" style={{ top: 280 }}>
      <div
        className="bg-slate-900/75 backdrop-blur-xl border border-white/15 rounded-3xl p-8 shadow-2xl text-white"
        style={{ width: 920, opacity: enter, transform: `translateY(${translateY}px) scale(${0.94 + enter * 0.06})` }}
      >
        <div className="flex items-center gap-4 mb-6">
          <div className="rounded-full bg-white/10 p-3">
            <PlatformIcon platform={segment.platform} />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 text-3xl font-bold">
              {segment.authorName || PLATFORM_LABEL[segment.platform]}
              {segment.platform !== "narrator" ? <BadgeCheck size={30} className="text-sky-400" /> : null}
            </div>
            <div className="text-2xl text-white/60">{segment.authorHandle || PLATFORM_LABEL[segment.platform]}</div>
          </div>
        </div>
        <p className="text-4xl leading-snug font-semibold">{segment.cardContent}</p>
        {segment.likesCount ? (
          <div className="flex items-center gap-3 mt-6 text-2xl text-rose-300">
            <Heart size={30} fill="currentColor" />
            {segment.likesCount}
          </div>
        ) : null}
      </div>
    </div>
  );
};
