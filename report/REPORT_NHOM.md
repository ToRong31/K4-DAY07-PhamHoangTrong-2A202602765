# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Sloppers
**Thành viên:** Hoàng Quốc Dũng, Lâm Hải Dương, Lê Thị Thùy Trang, Phạm Hoàng Trọng
**Ngày:** 20/09/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách bảo hành và trách nhiệm người mua/người bán trên TikTok Shop Việt Nam.

**Tại sao nhóm chọn chủ đề này?**
> Nhóm chọn chủ đề này vì các quy định bảo hành có cấu trúc heading rõ ràng, chứa điều kiện và trách nhiệm khác nhau giữa người mua với người bán, phù hợp để so sánh các chiến lược chunking. Nguồn là các trang chính sách công khai bằng tiếng Việt của TikTok Shop; corpus cũng cho phép kiểm chứng tác dụng của metadata filter theo `audience`.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | Bảo hành sản phẩm tân trang hoặc đã qua sử dụng | https://seller-vn.tiktok.com/university/essay?knowledge_id=383957212661520&lang=vi-VN | 20/09/2026 / 11/06/2025 | 8.509 | `seller`, `warranty-listing`, `vi` |
| 2 | Điều khoản bảo hành không công bằng | https://seller-vn.tiktok.com/university/essay?knowledge_id=7224191561467664&lang=vi-VN | 20/09/2026 / 29/06/2025 | 2.796 | `seller`, `seller-conduct`, `vi` |
| 3 | Hướng dẫn đăng bán và khai báo thông tin bảo hành | https://seller-vn.tiktok.com/university/essay?knowledge_id=6837791128454914&lang=vi-VN | 20/09/2026 / 17/03/2026 | 26.749 | `seller`, `listing-guidance`, `vi` |
| 4 | Quyền và trách nhiệm bảo hành của người mua | https://seller-vn.tiktok.com/university/essay?knowledge_id=761396473562887&lang=vi-VN | 20/09/2026 / 17/08/2026 | 1.033 | `buyer`, `warranty-policy`, `vi` |
| 5 | Trách nhiệm bảo hành của người bán | https://seller-vn.tiktok.com/university/essay?knowledge_id=761396473562887&lang=vi-VN | 20/09/2026 / 17/08/2026 | 1.068 | `seller`, `warranty-policy`, `vi` |
| 6 | Thông tin bảo hành sai lệch trên trang bán hàng | https://seller-vn.tiktok.com/university/essay?knowledge_id=7224191560681232&lang=vi-VN | 20/09/2026 / 16/09/2026 | 4.383 | `seller`, `listing-compliance`, `vi` |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | string | `tiktok-quy-che-bao-hanh-buyer` | Định danh ổn định của tài liệu gốc và hỗ trợ xóa toàn bộ chunk cùng tài liệu. |
| `source_url` | string | URL TikTok Shop University | Truy vết nội dung về đúng nguồn công khai. |
| `retrieved_at` | date | `2026-09-20` | Xác định thời điểm nhóm thu thập dữ liệu. |
| `document_version` | date/string | `2026-08-17` | Phân biệt phiên bản chính sách và phát hiện dữ liệu cũ. |
| `audience` | enum | `buyer`, `seller` | Lọc trước retrieval để tránh trộn quyền người mua với nghĩa vụ người bán. |
| `category` | string | `warranty-policy` | Thu hẹp tìm kiếm theo loại quy định. |
| `language` | string | `vi` | Tránh lấy nhầm tài liệu khác ngôn ngữ. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| Bảo hành hàng tân trang | FixedSizeChunker (`fixed_size`) | 10 | 850,90 | Có thể cắt ngang câu/bảng. |
| Bảo hành hàng tân trang | SentenceChunker (`by_sentences`) | 17 | 498,82 | Giữ câu nhưng dễ tách heading khỏi nội dung. |
| Bảo hành hàng tân trang | RecursiveChunker (`recursive`) | 12 | 707,00 | Giữ đoạn tốt hơn và độ dài tương đối ổn định. |
| Điều khoản không công bằng | FixedSizeChunker (`fixed_size`) | 4 | 699,00 | Có nguy cơ cắt giữa danh sách điều kiện. |
| Điều khoản không công bằng | SentenceChunker (`by_sentences`) | 5 | 557,80 | Giữ dấu câu nhưng một số mục danh sách vẫn dính nhau. |
| Điều khoản không công bằng | RecursiveChunker (`recursive`) | 4 | 697,50 | Giữ phần heading và danh sách tốt hơn. |
| Thông tin bảo hành sai lệch | FixedSizeChunker (`fixed_size`) | 5 | 876,60 | Kích thước đều nhưng không theo chủ đề. |
| Thông tin bảo hành sai lệch | SentenceChunker (`by_sentences`) | 10 | 436,40 | Dễ đọc nhưng tạo nhiều chunk hơn. |
| Thông tin bảo hành sai lệch | RecursiveChunker (`recursive`) | 7 | 624,29 | Cân bằng giữa kích thước và ranh giới đoạn. |

### Chiến lược của từng thành viên

Để tránh so sánh lệch do các report cá nhân ban đầu dùng bộ câu hỏi khác nhau, nhóm đã chạy lại cả bốn chiến lược trên cùng corpus 6 tài liệu, cùng 5 query, cùng OpenAI `text-embedding-3-small`, cùng `top_k=3` và cùng quy tắc metadata filter. Điểm dưới đây được chấm ở mức chunk chứa bằng chứng và được kiểm tra lại bằng câu trả lời grounded của `gpt-4.1-mini`.

**Thành viên 1 — Hoàng Quốc Dũng**
- **Loại chiến lược:** Custom — `HeadingSectionChunker` (semantic theo heading/section, `chunk_size=900`).
- **Mô tả & lý do chọn cho chủ đề này:** Tài liệu chính sách TikTok được tổ chức theo các mục như “Trách nhiệm của Người Bán” và “Quyền của Người Mua”, nên heading là ranh giới ngữ nghĩa tự nhiên. Mỗi section được giữ cùng đường dẫn heading; nếu section quá dài thì hạ xuống `RecursiveChunker` và gắn lại heading vào mọi chunk con để không mất chủ đề.
- **Code snippet (nếu custom):**
```python
for headings, body in sections:
    prefix = "\n".join(headings)
    if len(prefix) + len(body) <= chunk_size:
        chunks.append(f"{prefix}\n\n{body}")
    else:
        available = chunk_size - len(prefix) - 2
        for child in RecursiveChunker(chunk_size=available).chunk(body):
            chunks.append(f"{prefix}\n\n{child}")
```

**Thành viên 2 — Lê Thị Thùy Trang**
- **Loại chiến lược:** `FixedSizeChunker(chunk_size=500, overlap=100)`.
- **Mô tả & lý do chọn:** Đây là baseline đơn giản, tái lập dễ và có overlap 100 ký tự để giảm nguy cơ một điều kiện bị cắt đúng tại ranh giới chunk. Nhược điểm là ranh giới 500 ký tự không đi theo heading hoặc ý nghĩa của điều khoản.
- **Số chunk trên corpus chung:** 113.

**Thành viên 3 — Lâm Hải Dương**
- **Loại chiến lược:** `RecursiveChunker(chunk_size=500)`.
- **Mô tả & lý do chọn:** Ưu tiên tách theo đoạn, dòng, câu rồi mới tới từ/ký tự, vì vậy ít cắt ngang cấu trúc văn bản hơn fixed-size. Kích thước 500 làm chunk tập trung nhưng có thể tách một danh sách dài sang nhiều mảnh.
- **Số chunk trên corpus chung:** 120.

**Thành viên 4 — Phạm Hoàng Trọng**
- **Loại chiến lược:** Custom `HeadingSectionChunker(chunk_size=1200)`.
- **Mô tả & lý do chọn:** Tách theo heading Markdown và giữ đường dẫn mục; section dài mới hạ xuống recursive. Ngưỡng 1.200 ký tự giúp giữ các danh sách điều kiện dài trong cùng một chunk, đồng thời chỉ tạo 84 chunk — ít nhất trong bốn cấu hình.
- **Code snippet (custom):** Cùng nguyên tắc tách section và gắn lại heading như chiến lược của Dũng, nhưng dùng ngưỡng 1.200 ký tự.

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Hoàng Quốc Dũng | Heading/section semantic (`chunk_size=900`) | 7/10 | Giữ đường dẫn heading, Q1/Q4/Q5 đúng ở top-1; filter buyer đưa đáp án Q5 lên top-1. | Tạo 98 chunk và có thể phân mảnh các section anh em ngắn; Q2 đúng tài liệu nhưng sai section. |
| Lê Thị Thùy Trang | Fixed-size (`500`, overlap `100`) | 4/10 | Là chiến lược duy nhất đưa bằng chứng Q2 vào top-3; overlap giảm mất thông tin ở biên. | 113 chunk; chỉ Q1/Q2/Q4/Q5 có evidence nhưng đều ở rank 2 hoặc 3, Q3 thiếu chuỗi bằng chứng. |
| Lâm Hải Dương | Recursive (`chunk_size=500`) | 6/10 | Q1/Q4/Q5 có bằng chứng ở top-1; ranh giới chunk tự nhiên hơn fixed-size. | Nhiều chunk nhất (120); Q2 và Q3 đúng tài liệu nhưng top-3 không chứa đoạn trả lời. |
| Phạm Hoàng Trọng | Heading/section (`chunk_size=1200`) | **8/10** | Ít chunk nhất (84); Q1/Q3/Q4/Q5 đều có evidence ở top-1 và agent trả lời đúng. | Q2 vẫn lấy đúng tài liệu ở top-1 nhưng sai section, nên agent không thể liệt kê các hình thức bảo hành. |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> Trên corpus và 5 query chung, heading/section 1.200 ký tự của Phạm Hoàng Trọng tốt nhất với 8/10. Văn bản chính sách vốn được biên soạn theo mục và thường có danh sách điều kiện dài; ngưỡng lớn hơn giữ trọn danh sách Q3, còn heading lặp lại giữ chủ đề cho từng chunk. Tuy nhiên không có chiến lược nào thắng mọi câu: fixed-size của Trang là cấu hình duy nhất tìm được bằng chứng Q2 trong top-3, cho thấy kích thước/rank vẫn cần điều chỉnh theo dạng câu hỏi.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Người bán phải tuân thủ bao nhiêu nguyên tắc bắt buộc khi dùng nội dung do AI tạo để đăng sản phẩm? | Có 3 nguyên tắc: bảo đảm thông tin chính xác; không chỉnh sửa/phóng đại; kiểm tra thông tin trước khi đăng. | `tiktok-thong-tin-bao-hanh-sai-lech` — “Sử dụng Nội dung do AI tạo (AIGC)” |
| 2 | Hãy liệt kê các hình thức bảo hành được khai báo cho sản phẩm tân trang hoặc đã qua sử dụng. | Bảo hành quốc tế; bảo hành của nhà sản xuất; bảo hành của nhà cung cấp; hoặc không bảo hành. | `tiktok-bao-hanh-hang-tan-trang` — “Hình thức bảo hành” |
| 3 | Những điều kiện trả hàng hoặc bảo hành nào bị xem là điều khoản bán hàng không công bằng? | Không cho trả/hoàn tiền; giới hạn 3 ngày; bắt buộc video mở hộp; yêu cầu từ 3 sao mới được trả; hoặc vô hiệu bảo hành nếu không đánh giá 5 sao là các ví dụ bị cấm. | `tiktok-dieu-khoan-bao-hanh-bat-cong` — “Các ví dụ về điều khoản bán hàng không công bằng” |
| 4 | Khi sản phẩm có chính sách bảo hành, bên chịu trách nhiệm xử lý phải thực hiện những việc gì? | Người bán phải nhận sản phẩm và bảo hành/bảo trì theo đúng thông tin đã niêm yết. Dùng `metadata_filter={"audience": "seller"}`. | `tiktok-quy-che-bao-hanh-seller` — “Trách nhiệm bảo hành và bảo trì” |
| 5 | Khi yêu cầu bảo hành bị từ chối dù thời hạn vẫn còn, bên yêu cầu có thể làm gì? | Người mua có quyền khiếu nại hoặc khởi kiện người bán và có thể yêu cầu TikTok hỗ trợ. Dùng `metadata_filter={"audience": "buyer"}`. | `tiktok-quy-che-bao-hanh-buyer` — “Quyền và trách nhiệm của Người Mua” |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | AIGC có bao nhiêu nguyên tắc bắt buộc? | Đồng hạng: Dũng heading 900, Dương recursive 500, Trọng heading 1200 | Có, top-1 | Cả ba đưa evidence lên top-1 và agent trả lời đúng; 2/2. |
| 2 | Các hình thức bảo hành cho hàng tân trang/đã qua sử dụng | Fixed-size 500/100 — Lê Thị Thùy Trang | Có, top-2 | Chỉ fixed-size đưa danh sách bốn hình thức vào top-3; agent trả lời đúng; 1/2. |
| 3 | Điều khoản trả hàng/bảo hành không công bằng | Heading 1200 — Phạm Hoàng Trọng | Có, top-1 | Ngưỡng 1.200 giữ được danh sách dài; agent liệt kê đúng; 2/2. |
| 4 | Trách nhiệm xử lý bảo hành | Đồng hạng: Dũng, Dương, Trọng | Có, top-1 | Filter `seller`; cả ba đưa evidence lên top-1 và agent đúng; 2/2. |
| 5 | Xử lý khi bảo hành bị từ chối | Đồng hạng: Dũng, Dương, Trọng | Có, top-1 | Filter `buyer`; cả ba đưa evidence lên top-1 và agent đúng; 2/2. |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Có, rõ nhất ở câu 5. Với heading strategy, khi không filter thì cả ba kết quả đều thuộc tài liệu seller và không có đáp án; với `metadata_filter={"audience": "buyer"}`, chunk chứa quyền khiếu nại/khởi kiện lên top-1. Fixed-size và recursive cũng chỉ đưa chunk đáp án vào top-3 sau khi áp dụng filter, chứng minh filter thay đổi tập ứng viên chứ không chỉ trang trí metadata.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> - Chấm theo `doc_id` có thể thổi phồng chất lượng: ở Q2, gold doc đứng top-2 nhưng không chunk nào trong top-3 chứa danh sách cần trả lời.
> - Metadata filter có tác dụng thực tế: ở Q5, heading strategy chuyển từ ba kết quả sai audience sang đáp án buyer ở top-1.
> - Heading 1.200 đạt điểm tổng cao nhất, nhưng fixed-size lại thắng riêng Q2. Chunking tốt phụ thuộc cả cấu trúc tài liệu lẫn loại câu hỏi, không có một cấu hình thắng tuyệt đối.

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng một corpus và embedding, thay ranh giới chunk làm thứ hạng bằng chứng thay đổi rõ rệt. Chunk 500 ký tự tạo nhiều ứng viên tập trung nhưng dễ tách danh sách; heading 1.200 giữ được một điều khoản dài và đạt 8/10, trong khi heading 900 đạt 7/10 và recursive 500 đạt 6/10. Vì vậy nhóm chấm ở mức nội dung và câu trả lời agent, không coi “đúng `doc_id`” là đã truy xuất đúng.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Từ failure case Q2, nhóm nên gộp các section anh em quá ngắn trong cùng mục lớn và lưu thêm metadata `section_title`. Khi đánh giá, nhóm có thể tăng `top_k` hoặc bổ sung hybrid keyword/reranking để các cụm đặc trưng như “hình thức bảo hành” không bị section cùng chủ đề nhưng thiếu đáp án vượt lên trên.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 15 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 10 / 10 |
| Thuyết trình (Demo) | 5 / 5 |
| **Tổng phần nhóm** | **40 / 40** |
