import { AbsoluteFill, Audio, Series, staticFile } from "remotion";
import { fontFamily } from "./fonts";
import { BackgroundMusic } from "./components/BackgroundMusic";
import { BrollMedia } from "./components/news/BrollMedia";
import { NewsSubtitle } from "./components/news/NewsSubtitle";
import { TitleCard } from "./components/news/TitleCard";
import { VideoProps } from "./types/schema";

// Layout (1080x1920): B-roll fills the top, fades into a solid brand-colored panel holding the captions.
// Captions sit on the lower part of the fade, as in the reference layout.
const MEDIA_HEIGHT = 1350;
const FADE_HEIGHT = 290;
const WATERMARK_TOP = 1095;
const SUBTITLE_TOP = 1215;

// "News explainer" template: one B-roll per segment, hook title card on the first segment.
export const NewsComposition: React.FC<VideoProps> = ({
  topicTitle,
  topicHighlight,
  brandName,
  brandColor,
  bgmAudioFile,
  bgmVolume,
  segments,
}) => (
  <AbsoluteFill style={{ fontFamily, background: brandColor }}>
    <BackgroundMusic file={bgmAudioFile} volume={bgmVolume} />

    <Series>
      {segments.map((segment, index) => (
        <Series.Sequence key={segment.id} durationInFrames={segment.durationInFrames}>
          {segment.audioFile ? <Audio src={staticFile(segment.audioFile)} volume={1.0} /> : null}

          <div className="absolute left-0 right-0 top-0 overflow-hidden" style={{ height: MEDIA_HEIGHT }}>
            <BrollMedia segment={segment} />
          </div>
          <div
            className="absolute left-0 right-0"
            style={{
              top: MEDIA_HEIGHT - FADE_HEIGHT,
              height: FADE_HEIGHT + 2,
              background: `linear-gradient(to bottom, transparent, ${brandColor})`,
            }}
          />
          {/* The title card already shows the brand and would overlap the watermark. */}
          {index > 0 ? (
            <div
              className="absolute font-extrabold text-white"
              style={{ top: WATERMARK_TOP, left: 48, fontSize: 26, letterSpacing: 6, opacity: 0.55 }}
            >
              {brandName}
            </div>
          ) : null}

          {index === 0 ? (
            <TitleCard title={topicTitle} highlight={topicHighlight} brandName={brandName} brandColor={brandColor} />
          ) : (
            <NewsSubtitle subtitles={segment.subtitles} top={SUBTITLE_TOP} />
          )}
        </Series.Sequence>
      ))}
    </Series>
  </AbsoluteFill>
);
