import { AbsoluteFill, Audio, Loop, OffthreadVideo, Series, staticFile, useVideoConfig } from "remotion";
import { fontFamily } from "./fonts";
import { BackgroundMusic } from "./components/BackgroundMusic";
import { StoryTextBox, Paragraph } from "./components/story/StoryTextBox";
import { ThreadsPostCard } from "./components/story/ThreadsPostCard";
import { Segment, VideoProps } from "./types/schema";

// Roughly what fits in the text panel at 46px before it would run past mid-screen.
const PAGE_CHARS = 380;

// Splits story paragraphs (segments 2+) into pages; returns, per segment index, the index it starts its page at.
const pageStarts = (segments: Segment[]): number[] => {
  const starts: number[] = [];
  let start = 1;
  let chars = 0;
  segments.forEach((s, i) => {
    if (i === 0) {
      starts.push(0);
      return;
    }
    const len = s.subtitles.map((t) => t.text).join(" ").length;
    if (i > start && chars + len > PAGE_CHARS) {
      start = i;
      chars = 0;
    }
    chars += len;
    starts.push(start);
  });
  return starts;
};

const paragraphText = (s: Segment) => s.subtitles.map((t) => t.text).join(" ");

// "story" template: Threads post hook, then the story read out in a dark text panel over gameplay footage.
export const StoryComposition: React.FC<VideoProps> = ({
  topicTitle,
  brandName,
  bgVideoFile,
  bgVideoDurationInSeconds,
  bgmAudioFile,
  bgmVolume,
  segments,
}) => {
  const { fps } = useVideoConfig();
  const starts = pageStarts(segments);
  const hook = segments[0];

  return (
    <AbsoluteFill style={{ fontFamily, background: "#101014" }}>
      {bgVideoFile ? (
        <Loop durationInFrames={Math.max(1, Math.floor((bgVideoDurationInSeconds ?? 60) * fps))}>
          <OffthreadVideo src={staticFile(bgVideoFile)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </Loop>
      ) : (
        <AbsoluteFill style={{ background: "linear-gradient(160deg,#2b2d42,#101014)" }} />
      )}
      <BackgroundMusic file={bgmAudioFile} volume={bgmVolume} />

      <div
        className="absolute left-0 right-0 text-center font-extrabold text-white"
        style={{ top: 190, fontSize: 30, letterSpacing: 6, opacity: 0.7, textShadow: "0 2px 10px rgba(0,0,0,0.6)" }}
      >
        {brandName}
      </div>

      <Series>
        {segments.map((segment, index) => {
          const paragraphs: Paragraph[] = segments.slice(starts[index], index + 1).map((s, k, arr) => ({
            text: paragraphText(s),
            subtitles: s.subtitles,
            current: k === arr.length - 1,
          }));
          return (
            <Series.Sequence key={segment.id} durationInFrames={segment.durationInFrames}>
              {segment.audioFile ? <Audio src={staticFile(segment.audioFile)} volume={1.0} /> : null}
              {index === 0 ? (
                <ThreadsPostCard
                  username={hook.authorName}
                  community={hook.authorHandle}
                  likes={hook.likesCount}
                  text={topicTitle}
                />
              ) : (
                <StoryTextBox paragraphs={paragraphs} />
              )}
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  );
};
