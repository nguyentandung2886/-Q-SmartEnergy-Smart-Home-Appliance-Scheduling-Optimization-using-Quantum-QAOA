# Kịch bản thuyết trình — Q-SmartEnergy

> **Thời lượng mục tiêu:** 3–5 phút (bài pitch demo trực tiếp).
> Ban tổ chức chưa quy định mốc thời gian cụ thể trong rubric — nếu có giới hạn khác, co giãn phần Demo (Bước 3) trước.
>
> **Ngôn ngữ:** văn nói, đọc lên như đang đứng trước giám khảo. Chữ *in nghiêng* là lời thoại đọc thẳng; chữ thường là ghi chú thao tác cho presenter.
>
> **Chọn tài khoản demo:** dùng tài khoản **HỘ GIA ĐÌNH** (an toàn nhất). Đừng demo tài khoản doanh nghiệp có thiết bị "theo nhu cầu" tự khai — chúng bị đẩy mặc định vào 18h và dễ gây số liệu khó giải thích.
>
> **Kiểm tra trước khi vào phòng:** đã đăng nhập sẵn, có ít nhất 2–3 thiết bị linh hoạt (máy giặt, bình nước nóng…) trong danh sách, mạng chạy được (thời tiết lấy từ OpenWeatherMap).

---

## 1. Mở bài — Nỗi đau hóa đơn (≈ 40 giây)

> *"Kính chào ban giám khảo. Em xin bắt đầu bằng một con số thật trong biểu giá điện EVN đang áp dụng hôm nay.*
>
> *Giá điện sinh hoạt của mình là giá bậc thang lũy tiến — càng dùng nhiều, mỗi số điện càng đắt. Cụ thể: 100 số đầu tiên chỉ 1.984 đồng một kWh, nhưng khi vượt qua mốc 700 số, mỗi kWh nhảy lên 3.967 đồng — tức là **gần gấp đôi**. Cùng một cái máy giặt, chạy vào lúc bạn đã 'trót' dùng nhiều trong tháng thì tốn gần gấp đôi tiền so với đầu tháng. Đó là chưa kể VAT 8% cộng thêm trên toàn bộ hóa đơn.*
>
> *Với hộ đã lắp điện mặt trời mái nhà thì còn một cái đau nữa: tấm pin phát mạnh nhất vào buổi trưa, nhưng máy giặt, bình nóng lạnh lại hay chạy buổi tối — điện sạch làm ra thì bán rẻ hoặc bỏ phí, tối đến lại đi mua điện lưới giá cao.*
>
> *Bài toán 'nên bật thiết bị nào, vào giờ nào' để vừa né bậc giá cao, vừa hứng được nắng — chính là bài toán tối ưu tổ hợp. Và đó là chỗ tụi em dùng máy tính lượng tử."*

*(Ghi chú: số 1.984đ / 3.967đ / VAT 8% là hằng số thật trong `backend/core/calc.py`, theo QĐ 1279/QĐ-BCT ngày 09/5/2025. Không nói số tiết kiệm cụ thể ở đây — để nó tự hiện trên màn hình lúc demo.)*

---

## 2. Giới thiệu giải pháp (≈ 20 giây)

> *"Sản phẩm của tụi em tên là **Q-SmartEnergy**. Bạn chỉ cần khai thiết bị trong nhà và khung giờ được phép chạy; hệ thống mã hóa bài toán thành một mô hình QUBO rồi dùng thuật toán lượng tử QAOA trên Qiskit để tự xếp lịch — dời các tải linh hoạt vào đúng khung giờ rẻ nhất và nhiều nắng nhất, mà không bắt bạn phải hy sinh tiện nghi."*

*(Chỉ 2 câu. Không sa đà thuật ngữ — chi tiết kỹ thuật để dành cho phần chốt và phần phản biện.)*

---

## 3. Kịch bản demo 4 bước (≈ 2 phút 30)

Mở sẵn tab **"Tối ưu hóa lịch chạy"** (với hộ gia đình đây là *Bước 3*).

### Bước 1 — Chọn ngày & thời tiết tự động (≈ 20s)
Thao tác: bấm nút **"Hôm nay"** hoặc **"Ngày mai"** trên thanh Ngày tối ưu. Chỉ tay vào ô Thời tiết.

> *"Em chọn ngày cần tối ưu. Chú ý ô thời tiết ở đây — tụi em không bắt người dùng tự đoán trời nắng hay mưa: dữ liệu này được lấy tự động từ dự báo OpenWeatherMap theo đúng vị trí của bạn, vì lượng nắng quyết định trực tiếp việc nên dồn tải vào giờ nào."*

### Bước 2 — Bấm "Tối ưu hóa" & đọc hóa đơn (≈ 45s)
Thao tác: bấm nút đen **"Tối ưu hóa"**. Chờ vài giây, dải hóa đơn hiện ra: **Hóa đơn trước → Sau tối ưu → Tiết kiệm %**.

> *"Em bấm Tối ưu hóa. Đây là kết quả: hóa đơn trước, hóa đơn sau, và phần trăm tiết kiệm — tất cả bằng tiền đồng thật, tính theo đúng 5 bậc giá EVN cộng VAT.*
>
> *Và em xin nói thẳng luôn một điều mà giám khảo chắc chắn sẽ thắc mắc: **'hóa đơn trước' này là gì?** Nó là kịch bản người dùng chạy các thiết bị linh hoạt vào giờ **bất lợi nhất TRONG CHÍNH khung giờ họ cho phép** — chứ không phải một giờ bịa ra ngoài thói quen. Hai hóa đơn dùng y hệt phần thiết bị cố định, nên chênh lệch này cô lập đúng giá trị của việc xếp lịch. Đây là cận trên của tiết kiệm, và tụi em minh bạch về điều đó — chứ không giấu."*

*(Ghi chú: baseline worst-solar nằm ở `_worst_solar_schedule` / `_compute_schedule_bills`, `optimize_router.py`. Đây là câu trả lời Q2 — nói TRƯỚC khi bị hỏi.)*

### Bước 3 — Gantt tương tác & cảnh báo quá tải (≈ 45s)
Thao tác: chỉ vào biểu đồ Gantt. Kéo thử một khối tải linh hoạt (vd máy giặt) sang giờ khác — hóa đơn tính lại ngay. Chỉ vào dòng an toàn công suất phía dưới.

> *"Lịch được vẽ trực quan trên biểu đồ Gantt. Các khối màu là thiết bị, trục ngang là 24 giờ. Người dùng không bị ép — em có thể **kéo tay** một khối sang giờ khác, và hóa đơn được tính lại theo thời gian thực. Con số không hề cứng, không hề bịa.*
>
> *Phía dưới là lớp an toàn công suất: hệ thống cộng tổng công suất các thiết bị bật cùng lúc, nếu vượt ngưỡng an toàn của nhà — mặc định 5.000W — nó cảnh báo đỏ ngay và chỉ rõ thiết bị nào. Đây chính là ràng buộc quá tải mà tụi em đã đưa thẳng vào mô hình toán."*

### Bước 4 — Mở nắp capô: Phân tích thuật toán lượng tử (≈ 30s)
Thao tác: bấm nút **"Phân tích thuật toán lượng tử"**. Bảng so sánh QAOA hiện ra.

> *"Và đây là phần em muốn khoe nhất — bấm nút này, hệ thống chạy QAOA thật với nhiều cấu hình khác nhau và so từng cấu hình với nghiệm tối ưu tuyệt đối. Em sẽ nói về bảng này ngay bây giờ."*

*(Chuyển thẳng sang phần 4. Đừng dừng cho giám khảo kịp hỏi câu Q1 — mình chủ động trả lời.)*

---

## 4. Chốt — Bảng "Phân tích thuật toán lượng tử" & sự trung thực về QAOA (≈ 40 giây)

Bảng đang hiện trên màn hình có các cột thật: **reps · maxiter · Thời gian (s) · Năng lượng · Đạt tối ưu?**, cùng dòng tiêu đề ghi số qubit và nghiệm tối ưu toàn cục (brute-force). 4 cấu hình chạy từ rẻ đến đắt: (reps=1, maxiter=25), (1, 50), (2, 50), (3, 100).

> *"Bảng này chạy QAOA ở 4 mức tuning khác nhau, đo thời gian và so với nghiệm tối ưu tuyệt đối tìm bằng brute-force.*
>
> *Em xin chủ động trả lời câu hỏi khó nhất trước: **'QAOA của các em có thắng brute-force không?'** — Ở quy mô PoC 4–5 qubit này thì **KHÔNG**, và tụi em không giấu điều đó. Với 5 qubit chỉ có 2 mũ 5 tức 32 tổ hợp — brute-force duyệt hết trong tích tắc và chắc chắn ra nghiệm tối ưu. Code của tụi em còn **luôn đối chiếu với brute-force** và lấy nghiệm tốt hơn, để người dùng không bao giờ nhận một lịch dưới-tối-ưu.*
>
> *Vậy lượng tử để làm gì? Để chứng minh **toàn bộ pipeline lượng tử chạy thật** — từ QUBO, dựng mạch ansatz, chạy trên Aer, tới giải mã nghiệm. Vì bài lập lịch bùng nổ theo cấp số mũ: 20 thiết bị nhân 5 giờ ứng viên là 100 biến — brute-force cần 2 mũ 100 tổ hợp, không máy cổ điển nào duyệt nổi, còn QAOA vẫn cho nghiệm xấp xỉ. Lợi thế lượng tử xuất hiện khi bài đủ lớn, cỡ trên 20–25 qubit. Cái tụi em xây hôm nay là nền móng đúng cho quy mô đó.*
>
> *Em xin dừng ở đây và rất mong nhận câu hỏi từ ban giám khảo. Em cảm ơn."*

*(Ghi chú: 2^5=32, đối chiếu brute-force trong `QuantumScheduler.solve()`, ngưỡng lợi thế >20–25 qubit — tất cả ghi trong `quantum_runner.py` và comment `optimize_router.py:434-437`. Đây là câu trả lời Q1, nói CHỦ ĐỘNG.)*

---

## Phụ lục — Trả lời rút gọn cho 3 câu chốt (liếc ngay trước khi vào phòng)

**Q1 — "QAOA có thắng brute-force không? Không thì lượng tử để làm gì?"**
- Thẳng: ở 4–5 qubit thì KHÔNG — 2⁵ = 32 tổ hợp, brute-force nhanh hơn & chắc chắn tối ưu.
- Code TỰ ghi chú điều này và `solve()` luôn đối chiếu brute-force → không bao giờ trả nghiệm dưới-tối-ưu.
- Giá trị QAOA = chứng minh pipeline lượng tử chạy thật; bài thật bùng nổ 2ⁿ (20 thiết bị × 5 giờ = 100 biến = 2¹⁰⁰).
- Lợi thế lượng tử chỉ xuất hiện khi >20–25 qubit. Bảng phân tích trong app đo đúng trade-off đó.

**Q2 — "Hóa đơn 'trước' lấy đâu ra? Có chọn kịch bản xấu nhất cho % đẹp không?"**
- Baseline = chạy tải linh hoạt vào giờ bất lợi nhất **trong chính khung giờ người dùng cho phép** — không phải giờ bịa ngoài thói quen.
- Hai hóa đơn dùng CÙNG phần thiết bị cố định → chênh lệch cô lập đúng giá trị của việc xếp lịch.
- Thừa nhận: đây là cận trên của tiết kiệm. Kéo khối trên Gantt → hóa đơn tính lại realtime, số không bịa.

**Q3 — "Nhà không có điện mặt trời thì app vô dụng?"**
- Thừa nhận: PoC hiện giả định hộ 5kWp / 525 kWh tháng (số minh họa) — đúng phân khúc mục tiêu: hộ tải cao đã lắp solar, nhóm đau ví nhất.
- Với hộ không solar: vẫn còn trục **tránh nhảy bậc giá** + **cảnh báo quá tải công suất**.
- Cho người dùng khai công suất solar (kể cả 0) chỉ là thêm 1 trường — đã nằm trong roadmap. Nói TRƯỚC, đừng để bị phát hiện hard-code rồi mới thừa nhận.

**Bonus — nếu bị hỏi "EVN tính theo tháng, sao app có giá theo giờ?"**
- Hộ gia đình: mô hình **giá biên** — đến ngày thứ d trong tháng đã tích lũy X kWh, nên kWh tiếp theo rơi vào một bậc cụ thể; "nhảy bậc trong ngày" là tín hiệu optimizer cần.
- Doanh nghiệp: có giá theo giờ THẬT (TOU 3 khung, QĐ 963/QĐ-BCT) — vd hộ kinh doanh dưới 6kV: thấp điểm 1.918đ vs cao điểm 5.422đ/kWh (chưa VAT). App dùng đúng biểu giá đó.
