# bot-01: Bot tự động đăng bài mạng xã hội

Bot đăng bài theo lịch lên **Facebook, Instagram, X (Twitter) và TikTok**. Có hai cách đăng:

- **Trình duyệt (mặc định, không cần khoá API)**: bot tự mở trình duyệt bằng tài khoản bạn đã đăng nhập, bấm và gõ như người dùng.
- **API chính thức (dự phòng)**: an toàn hơn cho tài khoản nhưng phải xin khoá API (xem cuối trang).

Nguồn nội dung:
- **File trên máy bạn**: mỗi bài là một thư mục trong `posts/` (nội dung + ảnh/video).
- **Đăng lại tin**: lấy tin từ RSS thành **bản nháp** (tiêu đề + link nguồn). Bạn viết tóm tắt bằng lời của mình rồi duyệt. Bot không chép nguyên văn bài hay ảnh của người khác, để tránh vi phạm bản quyền.

## ⚠️ Rủi ro khi dùng chế độ trình duyệt

Điều khoản của cả 4 nền tảng **không cho phép tự động hoá ngoài API chính thức**. Tài khoản có thể bị yêu cầu xác minh, bị hạn chế tính năng hoặc bị khoá. Để giảm rủi ro, bot:

- đăng ít và giãn cách (mặc định tối đa 5 bài Facebook, 3 Instagram, 8 X, 2 TikTok mỗi ngày, cách nhau ít nhất 30 phút, nghỉ 30–120 giây giữa các nền tảng);
- gõ và bấm với tốc độ như người, hiện cửa sổ trình duyệt để bạn theo dõi;
- **không vượt captcha hay kiểm tra bảo mật**: gặp là dừng, chờ bạn tự xử lý trong cửa sổ trình duyệt (mặc định 5 phút), quá hạn thì bỏ qua bài đó.

Nên dùng với tài khoản bạn chấp nhận được rủi ro, và chuyển sang `POST_METHOD=api` cho nền tảng nào quan trọng.

Giao diện các trang thay đổi thường xuyên, nên đôi khi bot sẽ không tìm thấy nút và báo lỗi `Không tìm thấy phần tử`. Khi đó chỉ cần cập nhật selector trong `bot/browser/<nền tảng>.py`.

## Cài đặt

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
```

Đăng nhập một lần cho từng nền tảng (cửa sổ trình duyệt sẽ mở, bạn tự đăng nhập, xong bấm Enter):

```bash
python -m bot login facebook
python -m bot login instagram
python -m bot login x
python -m bot login tiktok
```

Phiên đăng nhập lưu trong thư mục `.profiles/` trên máy bạn (không đưa lên GitHub). Với Facebook, đặt `FB_TARGET_URL` trong `.env` nếu muốn đăng lên Page hoặc group thay vì bảng tin của bạn.

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
| Facebook | ✓ | ✓ nhiều ảnh | ✓ | Trình duyệt: trang cá nhân, Page hoặc group. API: chỉ Page |
| Instagram | ✗ | ✓ carousel ≤ 10 | ✓ Reels | Bắt buộc có ảnh/video |
| X | ✓ | ✓ ≤ 4 ảnh | ✓ 1 video | Tối đa 280 ký tự, bot tự cắt |
| TikTok | ✗ | chưa hỗ trợ | ✓ | Trình duyệt: đăng thẳng. API: vào hộp nháp |

## Chạy

```bash
python -m bot list              # xem hàng đợi: ✓ đã đăng, · chưa
python -m bot run --dry-run     # xem bài nào sắp đăng, không đăng thật
python -m bot run               # đăng các bài đã đến giờ
python -m bot run --only x      # chỉ đăng lên X
python -m bot loop              # chạy liên tục, kiểm tra mỗi 5 phút
python -m bot rss               # lấy tin từ config/feeds.yaml thành bản nháp
```

Bài vượt giới hạn trong ngày hoặc chưa đủ giãn cách sẽ được ghi `[hoãn]` và tự đăng ở lần chạy sau. Bot ghi lại bài đã đăng trong `state.json` nên chạy lại nhiều lần không bị đăng trùng. Nếu một nền tảng lỗi, lần chạy sau bot chỉ thử lại nền tảng đó.

Để bot tự chạy: để `python -m bot loop` mở trên máy, hoặc dùng **Task Scheduler** (Windows) / **cron** (macOS, Linux) chạy `python -m bot run` mỗi 15 phút.

## Dự phòng: dùng API chính thức

Đặt `POST_METHOD=api` (hoặc riêng từng nền tảng, ví dụ `POST_METHOD_X=api`) và điền khoá bên dưới. Chi tiết về chi phí, giới hạn và điều kiện duyệt của từng nền tảng có trong báo cáo nghiên cứu đi kèm dự án.

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
  pacing.py        giới hạn bài/ngày và giãn cách
  browser/         đăng bằng trình duyệt: facebook.py, instagram.py, x.py, tiktok.py
  media.py         tạo link công khai cho media
  platforms/       đăng bằng API: facebook.py, instagram.py, x.py, tiktok.py
posts/             bài viết của bạn
config/feeds.yaml  danh sách nguồn RSS
```

Chạy test: `pip install pytest && python -m pytest -q` (test trình duyệt chạy trên trang giả lập, không vào mạng xã hội thật)
