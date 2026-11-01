# DramaCast Studio MVP

Tạo video dọc 9:16 tự động: crawl bài đăng -> LLM viết kịch bản hài/cà khịa -> Gemini TTS (dự phòng edge-tts) đọc tiếng Việt -> Remotion render MP4.

Bốn template (chọn bằng `--template`, hoặc bỏ trống để hiện menu chọn khi chạy; API: `GET /templates`):
- `news`: tin tức giải thích — B-roll (Pixabay / Openverse / thư mục local) phía trên, khung màu thương hiệu chứa phụ đề phía dưới, thẻ tiêu đề mở đầu.
- `story`: đọc truyện Threads — nền gameplay (clip trong `remotion-video/public/assets/gameplay/`, hoặc clip "satisfying" từ Pixabay), thẻ bài đăng mở đầu, các đoạn truyện ngôi thứ nhất hiện dần theo lời đọc.
- `techcards`: bản tin motion graphics — nền pastel, mỗi cảnh một tấm thẻ (chữ lớn, ảnh minh hoạ, gạch đầu dòng, so sánh VS, trích dẫn, thẻ theo dõi kênh cuối video).
- `social`: radio Lofi — thẻ bài đăng glassmorphism trên nền video lặp.

## Cài đặt (Windows)

Cần Python 3.11+ và Node.js 20+.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Điền vào `backend/.env`:
- `LLM_API_KEY` (bắt buộc): key Groq miễn phí tại console.groq.com/keys. Mặc định dùng model `openai/gpt-oss-120b`.
  Muốn đổi sang endpoint khác theo chuẩn OpenAI (ví dụ gemini-web2api chạy local), sửa `LLM_BASE_URL` / `LLM_MODEL` / `LLM_JSON_MODE` theo mẫu trong `.env.example`.
- `PIXABAY_API_KEY` (nên có): đăng ký miễn phí, key hiện ở pixabay.com/api/docs sau khi đăng nhập.
  Không có key thì B-roll chỉ lấy từ các file bạn bỏ vào `remotion-video/public/assets/broll/`
  (đặt tên file theo nội dung, ví dụ `moss-brick-closeup.mp4`, để được ghép đúng cảnh); cảnh không có ảnh sẽ dùng nền tối.
  `OPENVERSE_FALLBACK=true` bật thêm ảnh CC0 từ Openverse, nhưng kết quả thường lạc đề.

```bash
cd remotion-video
npm install
```

### Viết kịch bản bằng Gemini Pro (qua gemini-web2api)

Proxy đặt ở `C:\Users\pc\Desktop\project\gemini-web2api`, chỉ nghe ở `127.0.0.1:8081`.

1. Dùng extension `gemini-cookie-sync-extension` (trong repo proxy) xuất `gemini-auth.json` vào thư mục proxy.
2. Lọc cookie và cập nhật `config.json` của proxy (bỏ cookie riêng của accounts.google.com, nếu không Gemini trả 401):
   ```bash
   python -I backend\scripts\prepare_gemini_auth.py C:\Users\pc\Desktop\project\gemini-web2api
   ```
3. Chạy proxy (để cửa sổ này mở):
   ```bash
   cd C:\Users\pc\Desktop\project\gemini-web2api; .\.venv\Scripts\python.exe gemini_web2api.py --config config.json
   ```
4. `backend/.env`: `LLM_BASE_URL=http://127.0.0.1:8081/v1`, `LLM_API_KEY` = key trong `api_keys` của proxy, `LLM_MODEL=gemini-3.1-pro`, `LLM_JSON_MODE=false`.

Khi cookie hết hạn (proxy báo 401), xuất lại bằng extension rồi chạy lại bước 2 và khởi động lại proxy.
`gemini-auth*.json` và `config.json` của proxy chứa phiên đăng nhập Google: không chia sẻ, không đưa lên git.

### Giọng đọc và nhạc nền

- **Giọng đọc:** `TTS_ENGINE=gemini` (mặc định) đọc cả kịch bản bằng Gemini TTS trong 1 lần gọi (cần `GEMINI_API_KEY` miễn phí ở aistudio.google.com/apikey),
  lấy mốc thời gian từng từ bằng Groq Whisper (`GROQ_API_KEY`). Lỗi hoặc thiếu key thì tự dùng edge-tts.
  Đổi giọng/kiểu đọc: `GEMINI_TTS_VOICE` (Leda, Puck, Aoede, Achird…), `GEMINI_TTS_STYLE`.
- **Nhạc nền:** mỗi video chọn ngẫu nhiên 1 bài trong `remotion-video/public/assets/bgm/` (8 bài lofi từ Pixabay Music,
  nguồn ghi trong `credits.json` và được chép vào `outputs/<jobId>_credits.txt`). Âm lượng `BGM_VOLUME` (mặc định 0.18), có fade-in/fade-out.
  File mp3 không có trong git (giấy phép Pixabay không cho phân phối lại file nhạc riêng lẻ): tải lại theo link trong `credits.json`.

## Chạy

Render một video từ dữ liệu mẫu:

```bash
cd backend
python -m app.pipeline --topic "Gen Z nuôi gạch rêu" --mock
```

Bỏ `--template` thì app hiện menu đánh số để chọn template; hoặc ghi thẳng, ví dụ `--template story`.
Dữ liệu mẫu khác: `--mock-file app\data\mock_posts_fake_office.json`.

Kết quả: `outputs/<jobId>.mp4`, kèm `<jobId>_script.json` (kịch bản) và `<jobId>_credits.txt` (nguồn ảnh).

Nếu bị lỗi giữa chừng (thường do edge-tts, xem bên dưới), chạy lại đúng kịch bản cũ mà không gọi LLM lần nữa:

```bash
python -m app.pipeline --template news --script ../outputs/<jobId>_script.json
```

Các câu đã đọc thành công được cache trong `backend/.cache/tts/`, nên lần chạy lại chỉ đọc phần còn thiếu.

**Lưu ý edge-tts:** từ cuối tháng 10/2026, server Microsoft hay trả về rỗng với giọng tiếng Việt theo từng đợt
([rany2/edge-tts#512](https://github.com/rany2/edge-tts/issues/512)). Pipeline tự đọc theo từng câu, thử lại với thời gian chờ tăng dần
và bỏ qua cảnh hỏng hẳn; nếu vẫn lỗi nhiều, đợi 10-15 phút rồi chạy lại với `--script`. Xem/chỉnh layout trực tiếp: `npm run studio` trong `remotion-video/`.

API: `uvicorn app.main:app --reload` rồi `POST /jobs` với `{"topic": "...", "template": "news"}`, theo dõi bằng `GET /jobs/{job_id}`.

Nhạc nền tùy chọn: đặt file ở `remotion-video/public/assets/bgm_lofi_chill.mp3` (bỏ qua nếu không có).
