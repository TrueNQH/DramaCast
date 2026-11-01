"""Turns crawled posts into a segmented Vietnamese narration script.

Calls any OpenAI-compatible /chat/completions endpoint (default Groq; a local gemini-web2api proxy
also works with LLM_JSON_MODE=false). The reply is parsed as JSON and validated, with a retry that
feeds the validation error back.
"""

from __future__ import annotations

import json
import logging
import re
import time

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_JSON_MODE, LLM_MODEL
from app.schemas import CardType, Platform, Sentiment, Template, Winner
from app.services.crawler import RawPost

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
RATE_LIMIT_RETRIES = 4
REQUEST_TIMEOUT_SECONDS = 240


class ScriptVersus(BaseModel):
    model_config = ConfigDict(extra="ignore")

    left_label: str = ""
    left_text: str = ""
    right_label: str = ""
    right_text: str = ""
    winner: Winner = ""


class ScriptCard(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: CardType
    kicker: str = ""
    headline: str = ""
    subline: str = ""
    items: list[str] = []
    versus: ScriptVersus | None = None


class ScriptSegment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    platform: Platform = "narrator"
    author_name: str = ""
    author_handle: str = ""
    card_content: str = ""
    likes_count: str = ""
    sentiment: Sentiment = "neutral"
    narration: str
    media_query: str = ""
    card: ScriptCard | None = None  # "techcards" only


class Script(BaseModel):
    model_config = ConfigDict(extra="ignore")

    topic_title: str
    topic_highlight: str = ""
    source_label: str = ""
    segments: list[ScriptSegment]


TONE = """Giọng văn: hài hước, lém lỉnh, hay cà khịa nhẹ, kể như đang "hóng drama" với hội bạn thân.
- Dùng tiếng lóng mạng Việt Nam vừa phải (kiểu "hóng", "toang", "u là trời", "cạn lời", "flex", "đỉnh nóc kịch trần") nhưng câu vẫn rõ nghĩa khi nghe.
- Có twist, so sánh bất ngờ, câu châm biếm; nhịp nhanh, câu ngắn.
- Cố tình gài các chi tiết gây tranh cãi để người xem muốn vào bình luận, chọn phe.
- Kết video bằng một câu hỏi khiêu khích người xem bình luận (ví dụ "Nuôi gạch là chữa lành hay chỉ là cô đơn đội lốt trend, bạn đứng về phe nào?").
- Giới hạn: trêu tình huống chứ không bôi nhọ cá nhân; không xúc phạm vùng miền, giới tính, tôn giáo, ngoại hình.
- Chỉ kể những sự việc, nhân vật, số liệu, lời trích có trong dữ liệu crawl; KHÔNG bịa thêm nhân vật hay sự kiện.
  Phần hài nằm ở cách bình luận, so sánh, cà khịa của người kể, không phải ở chi tiết bịa ra."""

OUTPUT_RULES = """Chỉ trả về MỘT object JSON hợp lệ, không markdown, không giải thích, đúng cấu trúc:
{"topic_title": str, "topic_highlight": str, "source_label": str,
"segments": [{"platform": "twitter"|"reddit"|"xiaohongshu"|"youtube"|"narrator",
"author_name": str, "author_handle": str, "card_content": str, "likes_count": str,
"sentiment": "neutral"|"drama"|"healing", "narration": str, "media_query": str}]}
source_label: tên miền của nguồn chính trong dữ liệu, ví dụ "threads.net", "reddit.com", "x.com", "xiaohongshu.com".
narration chỉ là chữ thuần để đọc TTS: không emoji, không hashtag, không ký hiệu, không ngoặc kép, có dấu câu đầy đủ.
narration là lời đọc liền mạch, KHÔNG mở đầu bằng nhãn cấu trúc như "Bối cảnh:", "Chi tiết hài:", "Kết:".
narration phải 100% tiếng Việt đọc được: KHÔNG chữ Hán/Nhật/Hàn, KHÔNG để nguyên câu tiếng Anh (dịch sang tiếng Việt),
không đọc username (thay bằng mô tả như "một cô nàng mê cây cảnh"); tên nền tảng viết theo cách người Việt hay đọc
(Xiaohongshu -> Tiểu Hồng Thư, X/Twitter -> Twitter, Reddit -> Reddit)."""

SOCIAL_PROMPT = f"""Bạn là biên kịch kênh video dọc bình luận drama mạng xã hội bằng tiếng Việt.
Viết lại các bài đăng dưới đây thành kịch bản kể chuyện.

{TONE}

Cấu trúc:
- 5 đến 8 segment. Segment đầu là lời mở gây tò mò (platform "narrator"), segment cuối là câu hỏi kéo bình luận (platform "narrator").
- Các segment giữa trích một bài đăng hoặc bình luận gây tranh cãi nhất: giữ platform, author_name, author_handle, likes_count theo dữ liệu gốc; sentiment "drama" khi gắt, "healing" khi dễ thương.
- card_content: bản dịch tiếng Việt ngắn gọn của bài đăng/bình luận, tối đa 200 ký tự. Với narrator, card_content là một câu chốt.
- narration: lời bình 1-3 câu, cà khịa về bài đăng đó.
- media_query: chuỗi rỗng.
- topic_title: tiêu đề hook ngắn dưới 60 ký tự. topic_highlight: chuỗi rỗng.

{OUTPUT_RULES}"""

NEWS_PROMPT = f"""Bạn là biên tập viên video dọc kiểu "tin tức giải thích" bằng tiếng Việt, nhưng kể theo phong cách bà tám hóng drama.
Dựa trên các bài đăng dưới đây, viết kịch bản đọc khoảng 55-70 giây.
Mạch: hook giật tít -> bối cảnh -> chi tiết hài/khó tin -> phe phản đối hoặc cảnh báo -> cà khịa ý nghĩa xã hội -> câu hỏi kéo bình luận.

{TONE}

Cấu trúc:
- topic_title: tiêu đề giật tít 50-80 ký tự, ví dụ "Vừa nghèo vừa cô đơn, Gen Z Trung Quốc đua nhau 'nuôi' cục gạch".
- topic_highlight: một cụm 2-5 từ CHÉP NGUYÊN VĂN từ topic_title, là phần gây tò mò nhất (sẽ tô màu).
- 10 đến 16 segment, mỗi segment là một cảnh hình ảnh, narration 1-2 câu (khoảng 12-30 từ).
- Segment đầu tiên: narration chính là topic_title.
- Segment cuối: câu hỏi khiêu khích người xem bình luận.
- media_query: 1-3 danh từ TIẾNG ANH chỉ một vật/cảnh cụ thể quay phim được, dùng để tìm stock footage,
  ví dụ "moss brick", "spray bottle", "moldy bread", "subway crowd", "woman smartphone".
  KHÔNG dùng khái niệm trừu tượng hay đồ họa (chart, trend, stress, question mark, illustration), không tên riêng,
  không từ chỉ góc máy (close up, aerial, timelapse).
- platform luôn "narrator"; author_name, author_handle, card_content, likes_count là chuỗi rỗng; sentiment "drama" hoặc "neutral".

{OUTPUT_RULES}"""

STORY_PROMPT = f"""Bạn là người viết truyện cho kênh video dọc kiểu "đọc truyện Threads/Reddit" bằng tiếng Việt:
nền là gameplay, người xem đọc theo từng đoạn chữ hiện ra trong lúc giọng đọc kể.
Dựa trên các bài đăng dưới đây, kể lại thành MỘT câu chuyện ngôi thứ nhất (xưng "tôi" hoặc "mình") như một bài tâm sự viral,
khoảng 50-70 giây đọc.

{TONE}
- Riêng template này được kể ở ngôi thứ nhất và kịch tính hoá cảm xúc, nhưng sự việc vẫn phải bám dữ liệu.

Cấu trúc:
- topic_title: câu mở bài đăng, ngắn như một status Threads (dưới 90 ký tự), gây tò mò, ví dụ "Ngày hôm nay dùng điện thoại đến đây là đủ rồi".
- Segment 1: narration chính là topic_title; author_name là username của người đăng gốc trong dữ liệu (bỏ @, hoặc "an_danh" nếu không có);
  author_handle là tên cộng đồng/chủ đề ngắn (ví dụ "viral", "tâm sự", "drama công sở"); likes_count lấy theo dữ liệu.
- Segment 2 trở đi: mỗi segment là MỘT đoạn văn của câu chuyện, 1-3 câu (15-40 từ), có diễn biến, có twist ở gần cuối.
- 8 đến 14 segment. Segment cuối: một câu chốt kèm câu hỏi hỏi ý kiến người xem.
- platform của mọi segment là "narrator" trừ segment 1 lấy theo nền tảng của bài gốc; card_content để chuỗi rỗng; media_query để chuỗi rỗng.
- topic_highlight: chuỗi rỗng.

{OUTPUT_RULES}"""

TECHCARDS_PROMPT = f"""Bạn là biên tập viên video dọc kiểu "bản tin motion graphics": mỗi cảnh là một tấm thẻ đồ hoạ
(chữ lớn, ảnh minh hoạ, gạch đầu dòng, so sánh) xuất hiện trong lúc giọng đọc bình luận, bằng tiếng Việt.
Dựa trên các bài đăng dưới đây, viết kịch bản khoảng 45-65 giây.

{TONE}

Cấu trúc:
- 7 đến 11 segment, narration 1-2 câu mỗi segment. Mỗi segment có thêm trường "card" mô tả tấm thẻ hiển thị:
  "card": {{"type": "hero"|"media"|"bullets"|"versus"|"quote"|"cta", "kicker": str, "headline": str, "subline": str,
            "items": [str], "versus": {{"left_label": str, "left_text": str, "right_label": str, "right_text": str, "winner": "left"|"right"|""}} hoặc null}}
- Các loại thẻ:
  - "hero": chữ thật lớn. headline 2-6 từ, là con số hoặc ý gây sốc (ví dụ "30 TỆ MỘT NGÀY"); kicker là nhãn nhỏ phía trên (ví dụ "GEN Z TRUNG QUỐC").
  - "media": một ảnh/clip minh hoạ trong khung bo góc. kicker là nhãn dán trên ảnh (2-5 từ); headline 2-5 từ hiện to bên dưới; subline 1 câu ngắn.
    Bắt buộc có media_query: 1-3 danh từ TIẾNG ANH chỉ vật/cảnh cụ thể quay được (ví dụ "office desk", "woman smartphone").
  - "bullets": headline là tiêu đề thẻ (2-5 từ), items gồm 2-4 ý, mỗi ý dưới 40 ký tự.
  - "versus": so sánh hai phe; left/right_label là nhãn nhỏ viết hoa (ví dụ "PHE ỦNG HỘ"), left/right_text 2-6 từ, winner là phe thắng hoặc "".
  - "quote": trích một bài đăng/bình luận trong dữ liệu. headline là câu trích (dịch tiếng Việt, dưới 120 ký tự);
    điền author_name, platform, likes_count của segment theo dữ liệu gốc.
  - "cta": thẻ kêu gọi theo dõi kênh. headline là câu hỏi kéo bình luận (dưới 70 ký tự).
- Segment 1 bắt buộc là "hero"; segment cuối bắt buộc là "cta" và narration chứa câu hỏi. Có ít nhất 2 thẻ "media" và một thẻ "bullets" hoặc "versus".
- Chữ trên thẻ là chữ ngắn để đọc lướt, KHÔNG chép nguyên narration, và luôn bằng tiếng Việt (câu trích tiếng Anh/Trung phải dịch).
  media_query chỉ điền cho thẻ "media", còn lại để chuỗi rỗng.
- topic_title: tiêu đề 40-70 ký tự; topic_highlight: chuỗi rỗng.

{OUTPUT_RULES}
Với template này mỗi segment có thêm trường "card" như mô tả ở trên."""

PROMPTS: dict[str, str] = {"social": SOCIAL_PROMPT, "news": NEWS_PROMPT, "story": STORY_PROMPT, "techcards": TECHCARDS_PROMPT}


def write_script(posts: list[RawPost], template: Template, topic_hint: str = "") -> Script:
    system = PROMPTS[template]
    payload = json.dumps([p.model_dump() for p in posts], ensure_ascii=False, indent=2)
    base = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Chủ đề gợi ý: {topic_hint or '(tự chọn từ dữ liệu)'}\n\nDữ liệu crawl:\n{payload}"},
    ]
    messages = base

    def ask_to_fix(reply: str, feedback: str) -> list[dict]:
        # Only the latest attempt is resent, keeping requests small for per-minute token limits.
        return [*base, {"role": "assistant", "content": reply}, {"role": "user", "content": feedback}]

    with httpx.Client(base_url=LLM_BASE_URL, timeout=REQUEST_TIMEOUT_SECONDS) as client:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                reply = _chat(client, messages)
            except httpx.HTTPStatusError as exc:
                # Groq answers 400 json_validate_failed when the model emits broken JSON in JSON mode.
                if exc.response.status_code != 400 or attempt == MAX_ATTEMPTS:
                    raise
                log.warning("Script attempt %d rejected by API: %s", attempt, exc.response.text[:300])
                continue
            try:
                script = Script.model_validate_json(_extract_json(reply))
            except (ValidationError, ValueError) as exc:
                log.warning("Script attempt %d invalid: %s", attempt, exc)
                messages = ask_to_fix(reply, f"JSON không hợp lệ: {exc}. Trả lại toàn bộ JSON đã sửa, không kèm gì khác.")
                continue
            _strip_labels(script)
            problems = _check(script, template)
            if problems and attempt < MAX_ATTEMPTS:
                log.warning("Script attempt %d rejected: %s", attempt, "; ".join(problems))
                messages = ask_to_fix(reply, "Kịch bản chưa đạt: " + "; ".join(problems) + ". Viết lại toàn bộ JSON, không kèm gì khác.")
                continue
            if script.topic_highlight not in script.topic_title:
                script.topic_highlight = ""
            return script
    raise RuntimeError(f"LLM did not return a valid script after {MAX_ATTEMPTS} attempts")


# "Bối cảnh: ...", "Chi tiết hài: ..." -- section names the model sometimes reads out.
LEADING_LABEL = re.compile(r"^\s*[^\s:,.!?]+(?:\s+[^\s:,.!?]+){0,3}\s*:\s+")


def _strip_labels(script: Script) -> None:
    for seg in script.segments[1:]:  # segment 1 reads the title verbatim
        seg.narration = LEADING_LABEL.sub("", seg.narration, count=1)


MIN_SEGMENTS = {"news": 10, "story": 8, "techcards": 7, "social": 5}


def _check(script: Script, template: Template) -> list[str]:
    problems = []
    segs = script.segments
    if len(segs) < MIN_SEGMENTS[template]:
        problems.append(f"cần ít nhất {MIN_SEGMENTS[template]} segment, hiện có {len(segs)}")
    if template == "news" and (not script.topic_highlight or script.topic_highlight not in script.topic_title):
        problems.append("topic_highlight phải là một cụm 2-5 từ chép nguyên văn từ topic_title")
    if segs and "?" not in segs[-1].narration:
        problems.append("segment cuối phải chứa một câu hỏi kéo bình luận (có dấu ?)")
    if template == "techcards" and segs:
        if any(s.card is None for s in segs):
            problems.append("mọi segment phải có trường card")
        else:
            if segs[0].card.type != "hero":
                problems.append('segment 1 phải là card "hero"')
            if segs[-1].card.type != "cta":
                problems.append('segment cuối phải là card "cta"')
            if any(s.card.type == "media" and not s.media_query for s in segs):
                problems.append('card "media" phải có media_query')
            if any(s.card.type == "versus" and not s.card.versus for s in segs):
                problems.append('card "versus" phải có trường versus')
    return problems


def _chat(client: httpx.Client, messages: list[dict]) -> str:
    if not LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY is not set (backend/.env)")
    body: dict = {"model": LLM_MODEL, "messages": messages, "stream": False}
    if LLM_JSON_MODE:
        body["response_format"] = {"type": "json_object"}
    for _ in range(RATE_LIMIT_RETRIES):
        resp = client.post("/chat/completions", headers={"Authorization": f"Bearer {LLM_API_KEY}"}, json=body)
        if resp.status_code != 429:
            break
        # Free tiers (e.g. Groq) cap tokens per minute; wait as long as the API asks.
        wait = min(float(resp.headers.get("retry-after", 20)), 90)
        log.warning("LLM rate limited, waiting %.0fs", wait)
        time.sleep(wait)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"].get("content")
    if not content:
        raise RuntimeError(f"{LLM_BASE_URL} returned an empty reply")
    return content


def _extract_json(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in reply")
    return text[start:end + 1]
