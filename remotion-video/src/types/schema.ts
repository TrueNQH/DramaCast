// Shared data contract. Must stay in sync with backend/app/schemas.py.
import { z } from "zod";

export const subtitleSchema = z.object({
  text: z.string(),
  startMs: z.number(),
  endMs: z.number(),
});

export const versusSchema = z.object({
  leftLabel: z.string(),
  leftText: z.string(),
  rightLabel: z.string(),
  rightText: z.string(),
  winner: z.enum(["left", "right", ""]),
});

// "techcards" template: what the scene shows (the narration is spoken over it).
export const cardSchema = z.object({
  type: z.enum(["hero", "media", "bullets", "versus", "quote", "cta"]),
  kicker: z.string(),
  headline: z.string(),
  subline: z.string(),
  items: z.array(z.string()),
  versus: versusSchema.nullable().optional(),
});

export const segmentSchema = z.object({
  id: z.number(),
  platform: z.enum(["twitter", "reddit", "xiaohongshu", "youtube", "narrator"]),
  authorName: z.string(),
  authorHandle: z.string(),
  cardContent: z.string(),
  likesCount: z.string(),
  sentiment: z.enum(["neutral", "drama", "healing"]),
  audioFile: z.string(),
  durationInSeconds: z.number(),
  durationInFrames: z.number(),
  subtitles: z.array(subtitleSchema),
  // "news" / "techcards": B-roll or card media.
  mediaFile: z.string().nullable().optional(),
  mediaType: z.enum(["image", "video"]).nullable().optional(),
  mediaDurationInSeconds: z.number().nullable().optional(),
  card: cardSchema.nullable().optional(),
});

export const videoPropsSchema = z.object({
  jobId: z.string(),
  template: z.enum(["social", "news", "story", "techcards"]).default("social"),
  topicTitle: z.string(),
  topicHighlight: z.string().default(""),
  brandName: z.string().default("DRAMACAST"),
  brandColor: z.string().default("#8F1210"),
  fps: z.number().default(30),
  width: z.number().default(1080),
  height: z.number().default(1920),
  bgVideoFile: z.string(),
  // "story" gameplay background length, used to loop it seamlessly.
  bgVideoDurationInSeconds: z.number().nullable().optional(),
  // "techcards" bottom pill, e.g. "threads.net".
  sourceLabel: z.string().default(""),
  bgmAudioFile: z.string(),
  bgmVolume: z.number().default(0.12),
  segments: z.array(segmentSchema),
});

export type Subtitle = z.infer<typeof subtitleSchema>;
export type Card = z.infer<typeof cardSchema>;
export type Segment = z.infer<typeof segmentSchema>;
export type VideoProps = z.infer<typeof videoPropsSchema>;
