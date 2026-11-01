import { AbsoluteFill, Audio, Series, staticFile } from "remotion";
import { fontFamily } from "./fonts";
import { BackgroundMusic } from "./components/BackgroundMusic";
import { LofiBackground } from "./components/LofiBackground";
import { SocialCard } from "./components/SocialCard";
import { SubtitleTrack } from "./components/SubtitleTrack";
import { NewsComposition } from "./NewsComposition";
import { StoryComposition } from "./StoryComposition";
import { TechCardsComposition } from "./TechCardsComposition";
import { VideoProps } from "./types/schema";

export const DramaCastComposition: React.FC<VideoProps> = (props) => {
  switch (props.template) {
    case "news":
      return <NewsComposition {...props} />;
    case "story":
      return <StoryComposition {...props} />;
    case "techcards":
      return <TechCardsComposition {...props} />;
    default:
      return <SocialComposition {...props} />;
  }
};

// Original "Lofi radio" template: glassmorphism social cards over a looping background.
const SocialComposition: React.FC<VideoProps> = ({ topicTitle, bgVideoFile, bgmAudioFile, bgmVolume, segments }) => (
  <AbsoluteFill style={{ fontFamily }} className="bg-black">
    <LofiBackground file={bgVideoFile} />
    <BackgroundMusic file={bgmAudioFile} volume={bgmVolume} />

    <div className="absolute left-0 right-0 flex justify-center" style={{ top: 120 }}>
      <div className="rounded-full bg-white/15 backdrop-blur-md border border-white/20 px-8 py-4 text-white text-4xl font-bold">
        {topicTitle}
      </div>
    </div>

    <Series>
      {segments.map((segment) => (
        <Series.Sequence key={segment.id} durationInFrames={segment.durationInFrames}>
          {segment.audioFile ? <Audio src={staticFile(segment.audioFile)} volume={1.0} /> : null}
          <SocialCard segment={segment} />
          <SubtitleTrack subtitles={segment.subtitles} />
        </Series.Sequence>
      ))}
    </Series>
  </AbsoluteFill>
);
