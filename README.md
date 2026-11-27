# bot-01: Bot tự động đăng bài mạng xã hội

Bot đăng bài theo lịch lên **Facebook Page, Instagram, X (Twitter) và TikTok**, chỉ dùng API chính thức của từng nền tảng (không giả lập trình duyệt, tránh bị khoá tài khoản).

Nguồn nội dung:
- **File trên máy bạn**: mỗi bài là một thư mục trong `posts/` (nội dung + ảnh/video).
- **Đăng lại tin**: lấy tin từ RSS thành **bản nháp** (tiêu đề + link nguồn). Bạn viết tóm tắt bằng lời của mình rồi duyệt. Bot không chép nguyên văn bài hay ảnh của người khác, để tránh vi phạm bản quyền.

## Cài đặt

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # rồi điền khoá API (xem phần bên dưới)
```

## Soạn bài

Tạo thư mục `posts/<tên-bài>/` gồm `post.yaml` và ảnh/video:

```yaml
status: approved                       # draft = chưa đăng
publish_at: 2026-12-01T09:00:00+07:00
platforms: [facebook, instagram, x, tiktok]
text: |
  Nội dung bài viết
link: https://example.com              # tuỳ chọn
media: [anh1.jpg, anh2.jpg]            # hoặc [video.mp4]
text_x: Bản ngắn riêng cho X           # tuỳ chọn, có text_facebook, text_instagram...
```

| Nền tảng | Chữ | Ảnh | Video | Ghi chú |
|---|---|---|---|---|
| Facebook Page | ✓ | ✓ (nhiều ảnh) | ✓ | Tải file trực tiếp từ máy |
| Instagram | ✗ | ✓ JPEG, carousel ≤ 10 | ✓ Reels | Ảnh cần link công khai (xem dưới) |
| X | ✓ | ✓ ≤ 4 ảnh | ✓ 1 video | Tối đa 280 ký tự, bot tự cắt |
| TikTok | ✗ | chưa hỗ trợ | ✓ | Mặc định vào hộp nháp TikTok |

## Chạy

```bash
python -m bot list              # xem hàng đợi: ✓ đã đăng, · chưa
python -m bot run --dry-run     # xem bài nào sắp đăng, không đăng thật
python -m bot run               # đăng các bài đã đến giờ
python -m bot run --only x      # chỉ đăng lên X
python -m bot loop              # chạy liên tục, kiểm tra mỗi 5 phút
python -m bot rss               # lấy tin từ config/feeds.yaml thành bản nháp
```

Bot ghi lại bài đã đăng trong `state.json` nên chạy lại nhiều lần không bị đăng trùng. Nếu một nền tảng lỗi, lần chạy sau bot chỉ thử lại nền tảng đó.

Để bot tự chạy: để `python -m bot loop` mở trên máy, hoặc dùng **Task Scheduler** (Windows) / **cron** (macOS, Linux) chạy `python -m bot run` mỗi 15 phút.

## Lấy khoá API

### Facebook Page + Instagram (miễn phí)
1. Cần một **Facebook Page** và tài khoản **Instagram chuyên nghiệp** (Business/Creator) liên kết với Page.
2. Vào [developers.facebook.com](https://developers.facebook.com/), tạo app, chọn use case quản lý Trang và Instagram.
3. Trong Graph API Explorer, cấp quyền `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `publish_video`, `instagram_basic`, `instagram_content_publish`.
4. Đổi user token sang loại dài hạn, gọi `GET /me/accounts` để lấy **Page token** → điền `FB_PAGE_ID`, `FB_PAGE_TOKEN`.
5. Gọi `GET /{page-id}?fields=instagram_business_account` để lấy `IG_USER_ID`.

Chỉ bạn dùng app (bạn là admin) thì **không cần App Review**. Bot chỉ đăng được lên Page, không đăng lên trang cá nhân hay group.

**Link công khai cho ảnh Instagram**: Instagram tự tải ảnh từ một đường link. Chọn một cách:
- `MEDIA_BASE_URL`: nếu repo công khai, dùng `https://raw.githubusercontent.com/<user>/bot-01/main/posts` (phải push ảnh lên trước).
- `S3_BUCKET`: Cloudflare R2 (có gói miễn phí) hoặc S3, cài thêm `pip install boto3`.

Video Reels được tải thẳng từ máy, không cần link.

### X (trả theo lượt)
1. Vào [console.x.com](https://console.x.com/), tạo app, đặt quyền **Read and Write**, nạp một ít tiền (ví dụ $5).
2. Tạo **API Key/Secret** và **Access Token/Secret** → điền 4 biến `X_...`.
3. Chi phí khoảng **$0.015 mỗi bài**, nhưng **$0.20 nếu bài có link**. Đặt `X_INCLUDE_LINKS=false` để tiết kiệm.
4. Nên bật nhãn "Automated" cho tài khoản trong cài đặt X.

### TikTok
1. Vào [developers.tiktok.com](https://developers.tiktok.com/), tạo app, thêm **Login Kit** và **Content Posting API**, khai báo Redirect URI.
2. Xin scope `video.upload` và chờ duyệt (vài ngày đến 2 tuần).
3. Điền `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REDIRECT_URI`, rồi chạy `python -m bot tiktok-login` một lần.

**Vì sao mặc định vào hộp nháp?** App chưa qua kiểm duyệt của TikTok chỉ đăng được ở chế độ riêng tư, và TikTok không duyệt công cụ dùng nội bộ hay app sao chép nội dung từ nền tảng khác. Vì vậy bot đẩy video vào **hộp nháp TikTok**, bạn mở app TikTok và bấm đăng. Muốn thử đăng thẳng (riêng tư): `TIKTOK_MODE=direct`. Không chèn logo/watermark/link quảng cáo lên video TikTok.

## Cấu trúc

```
bot/
  __main__.py      dòng lệnh
  store.py         hàng đợi bài và trạng thái đã đăng
  rss.py           lấy tin thành bản nháp
  media.py         tạo link công khai cho media
  platforms/       facebook.py, instagram.py, x.py, tiktok.py
posts/             bài viết của bạn
config/feeds.yaml  danh sách nguồn RSS
```

Chạy test: `pip install pytest && python -m pytest -q`
