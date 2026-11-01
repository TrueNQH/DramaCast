import "./style.css";
import { CalculateMetadataFunction, Composition } from "remotion";
import { DramaCastComposition } from "./Composition";
import { VideoProps, videoPropsSchema } from "./types/schema";

// Studio preview only; real renders pass public/current_job/inputProps.json via --props.
const defaultProps: VideoProps = {
  jobId: "preview",
  template: "news",
  topicTitle: "Vừa nghèo vừa cô đơn, Gen Z đua nhau 'nuôi' cục gạch",
  topicHighlight: "đua nhau 'nuôi'",
  brandName: "DRAMACAST",
  brandColor: "#8F1210",
  fps: 30,
  width: 1080,
  height: 1920,
  bgVideoFile: "assets/bg_rain_cafe.mp4",
  sourceLabel: "",
  bgmAudioFile: "",
  bgmVolume: 0.12,
  segments: [
    {
      id: 1, platform: "narrator", authorName: "", authorHandle: "", cardContent: "",
      likesCount: "", sentiment: "neutral", audioFile: "",
      durationInSeconds: 3, durationInFrames: 90, subtitles: [],
    },
    {
      id: 2, platform: "narrator", authorName: "", authorHandle: "", cardContent: "",
      likesCount: "", sentiment: "neutral", audioFile: "",
      durationInSeconds: 4, durationInFrames: 120,
      subtitles: [
        { text: "Một số người trẻ đang chọn cách bầu bạn kỳ lạ:", startMs: 0, endMs: 2000 },
        { text: "nuôi một cục gạch", startMs: 2000, endMs: 3600 },
      ],
    },
  ],
};

const calculateMetadata: CalculateMetadataFunction<VideoProps> = ({ props }) => {
  const total = props.segments.reduce((sum, s) => sum + s.durationInFrames, 0);
  return {
    durationInFrames: Math.max(1, total),
    fps: props.fps,
    width: props.width,
    height: props.height,
  };
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="DramaCastVideo"
    component={DramaCastComposition}
    schema={videoPropsSchema}
    defaultProps={defaultProps}
    calculateMetadata={calculateMetadata}
    durationInFrames={210}
    fps={30}
    width={1080}
    height={1920}
  />
);
