import { AbsoluteFill, Audio, interpolate, Series, staticFile, useCurrentFrame } from "remotion";
import { fontFamily } from "./fonts";
import { BackgroundMusic } from "./components/BackgroundMusic";
import { BulletsCard, CtaCard, HeroCard, MediaCard, QuoteCard, VersusCard } from "./components/techcards/Cards";
import { BrandHeader, PastelBackground, SourcePill } from "./components/techcards/Chrome";
import { Card, Segment, VideoProps } from "./types/schema";

const EXIT_FRAMES = 6;

const Scene: React.FC<{ segment: Segment; props: VideoProps }> = ({ segment, props }) => {
  const frame = useCurrentFrame();
  const exit = interpolate(frame, [segment.durationInFrames - EXIT_FRAMES, segment.durationInFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // A segment without a card still gets something on screen: its narration as a hero line.
  const card: Card = segment.card ?? {
    type: "hero",
    kicker: "",
    headline: "",
    subline: segment.subtitles.map((s) => s.text).join(" "),
    items: [],
  };

  let body: React.ReactNode;
  switch (card.type) {
    case "media":
      body = <MediaCard card={card} segment={segment} source={props.sourceLabel} />;
      break;
    case "bullets":
      body = <BulletsCard card={card} segment={segment} />;
      break;
    case "versus":
      body = <VersusCard card={card} segment={segment} />;
      break;
    case "quote":
      body = <QuoteCard card={card} segment={segment} />;
      break;
    case "cta":
      body = <CtaCard card={card} segment={segment} brandName={props.brandName} brandColor={props.brandColor} />;
      break;
    default:
      body = <HeroCard card={card} />;
  }
  return <AbsoluteFill style={{ opacity: exit }}>{body}</AbsoluteFill>;
};

// "techcards" template: pastel motion-graphics news cards, one card per segment.
export const TechCardsComposition: React.FC<VideoProps> = (props) => (
  <AbsoluteFill style={{ fontFamily }}>
    <PastelBackground />
    <BackgroundMusic file={props.bgmAudioFile} volume={props.bgmVolume} />
    <BrandHeader name={props.brandName} color={props.brandColor} />
    <SourcePill label={props.sourceLabel} />
    <Series>
      {props.segments.map((segment) => (
        <Series.Sequence key={segment.id} durationInFrames={segment.durationInFrames}>
          {segment.audioFile ? <Audio src={staticFile(segment.audioFile)} volume={1.0} /> : null}
          <Scene segment={segment} props={props} />
        </Series.Sequence>
      ))}
    </Series>
  </AbsoluteFill>
);
