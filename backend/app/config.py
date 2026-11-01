import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent
load_dotenv(BACKEND_DIR / ".env")

REMOTION_DIR = ROOT_DIR / "remotion-video"
PUBLIC_DIR = REMOTION_DIR / "public"
JOB_DIR = PUBLIC_DIR / "current_job"
OUTPUTS_DIR = ROOT_DIR / "outputs"
MOCK_DATA_FILE = Path(__file__).resolve().parent / "data" / "mock_posts.json"

# OpenAI-compatible chat endpoint; default is Groq (key: https://console.groq.com/keys).
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
# Sends response_format={"type": "json_object"}; turn off for endpoints that reject it (e.g. gemini-web2api).
LLM_JSON_MODE = os.getenv("LLM_JSON_MODE", "true").lower() == "true"
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")
LOCAL_BROLL_DIR = PUBLIC_DIR / "assets" / "broll"
# "story" template background: a random clip from here, else a Pixabay "satisfying" clip.
GAMEPLAY_DIR = PUBLIC_DIR / "assets" / "gameplay"
# Openverse search relevance is poor (often unrelated portraits of real people), so it is opt-in.
OPENVERSE_FALLBACK = os.getenv("OPENVERSE_FALLBACK", "false").lower() == "true"
# Command that prints crawled posts as JSON on stdout; "{query}" is replaced by the topic.
AGENT_REACH_CMD = os.getenv("AGENT_REACH_CMD", "")

# "gemini": whole script in one Gemini TTS call, word timings from Groq Whisper (falls back to edge on error).
# "edge": per-sentence edge-tts with its own word boundaries.
TTS_ENGINE = os.getenv("TTS_ENGINE", "gemini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")  # free key: https://aistudio.google.com/apikey
GEMINI_TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
GEMINI_TTS_VOICE = os.getenv("GEMINI_TTS_VOICE", "Leda")
GEMINI_TTS_STYLE = os.getenv(
    "GEMINI_TTS_STYLE",
    "native Vietnamese Gen Z gossip narrator, playful and teasing, lively, speaking fairly rapidly with natural rhythm",
)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-large-v3")

# Background music: one track is picked at random per video from this folder.
BGM_DIR = PUBLIC_DIR / "assets" / "bgm"
# 0.18 sits ~23 dB under the narration (measured on a rendered mix).
BGM_VOLUME = float(os.getenv("BGM_VOLUME", "0.18"))

TTS_VOICE = os.getenv("TTS_VOICE", "vi-VN-HoaiMyNeural")
# Upbeat pacing for the humorous drama scripts.
TTS_RATE = os.getenv("TTS_RATE", "+12%")
TTS_PITCH = os.getenv("TTS_PITCH", "+2Hz")
SEGMENT_PADDING_SECONDS = float(os.getenv("SEGMENT_PADDING_SECONDS", "0.25"))
