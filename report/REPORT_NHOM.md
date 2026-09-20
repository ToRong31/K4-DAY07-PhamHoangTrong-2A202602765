# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** [Tên nhóm]
**Thành viên:** [Họ tên từng thành viên]
**Ngày:** [Ngày nộp]

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách bảo hành và thông tin đăng bán dành cho người bán trên TikTok Shop Việt Nam.

**Tại sao nhóm chọn chủ đề này?**
> Bộ 5 tài liệu cùng chủ đề nhưng khác độ dài và mức phân cấp heading, phù hợp để so sánh cách chia chunk. Tài liệu quy chế dài hơn nhiều so với các tài liệu còn lại, giúp kiểm tra trường hợp heading thưa và mục quá dài.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | Bảo hành hàng tân trang/đã qua sử dụng | [TikTok Shop](https://seller-vn.tiktok.com/university/essay?knowledge_id=383957212661520&lang=vi-VN) | 2026-09-20 / không nêu | 8.509 | `audience`, `category`, `language`, nguồn, ngày lấy, phiên bản |
| 2 | Điều khoản bảo hành không công bằng | [TikTok Shop](https://seller-vn.tiktok.com/university/essay?knowledge_id=7224191561467664&lang=vi-VN) | 2026-09-20 / không nêu | 2.796 | Như trên |
| 3 | Hướng dẫn đăng bán và khai báo bảo hành | [TikTok Shop](https://seller-vn.tiktok.com/university/essay?knowledge_id=6837791128454914&lang=vi-VN) | 2026-09-20 / không nêu | 26.749 | Như trên |
| 4 | Quy chế bảo hành và bảo trì | [TikTok Shop](https://seller-vn.tiktok.com/university/essay?knowledge_id=761396473562887&lang=vi-VN) | 2026-09-20 / không nêu | 160.559 | Như trên |
| 5 | Thông tin bảo hành sai lệch | [TikTok Shop](https://seller-vn.tiktok.com/university/essay?knowledge_id=7224191560681232&lang=vi-VN) | 2026-09-20 / không nêu | 4.383 | Như trên |

Số ký tự tính trên phần nội dung sau metadata đầu file, không tính front matter.

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] 5 file ghi `license_or_permission: public-source`; cần kiểm tra thủ công lại nguồn trước khi nộp.
- [x] Mỗi file có `source_url`, `retrieved_at`, `document_version` trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `source_url`, `retrieved_at`, `document_version` | chuỗi | URL nguồn, `2026-09-20`, `not-stated` | Truy vết và kiểm tra độ mới của chính sách. |
| `audience` | chuỗi | `seller`, `both` | Lọc theo đối tượng trước khi truy xuất. |
| `category`, `language` | chuỗi | `warranty-policy`, `vi` | Giới hạn chủ đề và ngôn ngữ. |
| `heading_path`, `heading_level` | chuỗi, số | `4. Mô tả sản phẩm > 4.2 Tình trạng vật lý`, `3` | Chỉ ra đúng mục nguồn của chunk. |
| | | | |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

Đã chạy với `chunk_size=1200`; `fixed_size` dùng overlap 50 ký tự, `by_sentences` gom 3 câu, `recursive` ưu tiên đoạn/dòng/câu/từ. Cột heading là chiến lược riêng của Trọng với giới hạn 1200 ký tự, tách tiếp mục quá dài. Số liệu tái tạo bằng `py -3.11 -m scripts.heading_baseline`.

329 chunk theo heading đã được xuất ra `data/seller-warranty-policy/chunks/heading-1200.jsonl` bằng lệnh `py -3.11 -m scripts.heading_baseline --save-chunks`. Mỗi dòng có `id`, `content` và `metadata` để nạp trực tiếp thành `Document`.

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| Điều khoản không công bằng | FixedSizeChunker (`fixed_size`) | 3 | 965,3 | Có thể cắt ngang mục. |
| Điều khoản không công bằng | SentenceChunker (`by_sentences`) | 5 | 557,8 | Giữ dấu câu; có thể mất heading. |
| Điều khoản không công bằng | RecursiveChunker (`recursive`) | 3 | 932,0 | Giữ ranh giới đoạn khi có thể. |
| Điều khoản không công bằng | Theo heading (`by_heading`) | 5 | 596,8 | Giữ đường dẫn mục. |
| Hướng dẫn đăng bán | FixedSizeChunker (`fixed_size`) | 24 | 1.162,5 | Có thể cắt giữa điều khoản. |
| Hướng dẫn đăng bán | SentenceChunker (`by_sentences`) | 62 | 429,4 | Có chunk dài 2.228 ký tự. |
| Hướng dẫn đăng bán | RecursiveChunker (`recursive`) | 28 | 955,3 | Giữ ranh giới đoạn khi có thể. |
| Hướng dẫn đăng bán | Theo heading (`by_heading`) | 49 | 643,3 | Giữ đường dẫn mục; 7 mục cần tách tiếp. |
| Quy chế bảo hành | FixedSizeChunker (`fixed_size`) | 140 | 1.196,5 | Nhiều ranh giới cắt giữa ý. |
| Quy chế bảo hành | SentenceChunker (`by_sentences`) | 239 | 670,2 | Có chunk dài 4.594 ký tự. |
| Quy chế bảo hành | RecursiveChunker (`recursive`) | 212 | 757,4 | Giữ ranh giới khi văn bản cho phép. |
| Quy chế bảo hành | Theo heading (`by_heading`) | 248 | 750,4 | Giữ đường dẫn mục; 27 mục cần tách tiếp. |

### Chiến lược của từng thành viên

> Mỗi thành viên điền một khối dưới đây (copy thêm nếu nhóm có nhiều hơn 3 người).

**Thành viên 1 — Phạm Hoàng Trọng**
- **Loại chiến lược:** Custom `by_heading`, đã nhận vai.
- **Mô tả & lý do chọn cho chủ đề này:** Tách theo `#` đến `######` của Markdown, lưu toàn bộ đường dẫn mục vào metadata. Mục dài hơn 1200 ký tự được tách đệ quy trong phạm vi mục đó và gắn lại đường dẫn heading, để câu trả lời truy được điều khoản gốc.
- **Code snippet (nếu custom):**
```python
def chunk_policy(path: Path, max_chars: int = 1200) -> list[Document]:
    """Tách theo Markdown headings, mục quá dài được tách đệ quy giữ heading path."""
    base_metadata, body = read_policy(path)
    sections, stack, current, current_level = [], [], [], 0
    for line in body.splitlines():
        match = HEADING.match(line)
        if match:
            if current: sections.append((list(stack), current_level, list(current)))
            level, title = len(match.group(1)), match.group(2).strip()
            stack = stack[:level - 1] + [title]
            current_level, current = level, []
        else:
            current.append(line)
    if current: sections.append((list(stack), current_level, list(current)))

    output = []
    for path_parts, level, lines in sections:
        section_text = "\n".join(lines).strip()
        heading_path = " > ".join(path_parts) if path_parts else base_metadata["title"]
        prefix = f"{heading_path}\n\n"
        budget = max_chars - len(prefix)
        pieces = ([section_text] if len(section_text) <= budget
                  else RecursiveChunker(chunk_size=budget).chunk(section_text))
        for index, piece in enumerate(pieces):
            output.append(Document(
                id=f"{path.stem}#{len(output)}",
                content=prefix + piece,
                metadata={**base_metadata, "heading_path": heading_path, "heading_level": level,
                          "section_part": index + 1, "section_parts": len(pieces),
                          "split_method": "heading" if len(pieces) == 1 else "heading+recursive"},
            ))
    return output
```

**Phân vai còn lại:** Chưa có tên hoặc lựa chọn của các thành viên khác trong repo. Nhóm cần ghi mỗi người vào một chiến lược khác (`fixed_size`, `by_sentences`, `recursive`, hoặc một biến thể metadata được xác định rõ) trước khi so sánh; bảng này chưa xác nhận được rằng không ai trùng Trọng.

**Nhận xét baseline:** Tài liệu quy chế chiếm 248/329 chunk heading của cả tập (75,4%) và chứa nhiều mục ngoài bảo hành. Khi chạy truy xuất, nên kiểm tra top-3 có bị tài liệu này lấn át không và thử lọc `category`/`audience` hoặc giới hạn theo `heading_path`. Baseline trên đây chỉ đo cấu trúc chunk; chưa phải điểm chất lượng truy xuất vì `MockEmbedder` không biểu diễn ngữ nghĩa tiếng Việt.

**Thành viên 2 — [Tên]**
- **Loại chiến lược:**
- **Mô tả & lý do chọn:**
- **Code snippet (nếu custom):**

**Thành viên 3 — [Tên]**
- **Loại chiến lược:**
- **Mô tả & lý do chọn:**
- **Code snippet (nếu custom):**

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Phạm Hoàng Trọng (R3) | Heading, giới hạn 1.200 ký tự; mục dài tách recursive | 2/10 | Giữ đường dẫn điều khoản, Q4 và Q5 có đáp án ở top-2 | Q1 đúng tài liệu nhưng sai mục; Q3 đáp án nằm rải ở nhiều mục |
| | | | | |
| | | | | |

**Failure case của R3:** Q1 có `tiktok-quy-che-bao-hanh` ở top-1 nhưng chunk đó chỉ là phần mở đầu, không chứa thông tin người bán phải bảo hành theo nội dung đã niêm yết. Chunk chứa đủ hai cụm bằng chứng xếp thứ 5. Nguyên nhân: nhiều mục trong quy chế cùng nhắc tới bảo hành nên embedding ưu tiên độ gần chủ đề hơn điều khoản trả lời trực tiếp. Hướng sửa: thử rerank theo nội dung và `heading_path`, hoặc mở rộng sang mục con lân cận khi chunk đầu chỉ là heading/giới thiệu. Bảng so sánh với thành viên khác sẽ bổ sung khi họ gửi kết quả cùng 5 câu hỏi.

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> *Viết 2-3 câu — đây là phần được đánh giá cao nhất (khả năng suy nghĩ & giải thích):*

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> *Viết 2-3 câu:*

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> Quan sát R3: kiểm `doc_id` riêng sẽ chấm nhầm Q1 là đúng, trong khi top-3 không chứa câu trả lời; phải kiểm nội dung của chunk. Ở Q4, kết quả top-3 có lọc `audience=seller` giống hệt không lọc nên câu này chưa cho thấy lợi ích của metadata filter trên tập tài liệu hiện có.

**Bài học rút ra khi so sánh trong nhóm:**
> *Viết 2-3 câu — cùng tài liệu nhưng chiến lược khác nhau dẫn tới khác biệt gì?*

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> *Viết 2-3 câu:*

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | / 10 |
| Thiết kế chiến lược (Strategy Design) | / 15 |
| Chất lượng truy xuất (Retrieval Quality) | / 10 |
| Thuyết trình (Demo) | / 5 |
| **Tổng phần nhóm** | **/ 40** |
