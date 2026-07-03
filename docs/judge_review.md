# Báo cáo Giám khảo giả lập — Q-SmartEnergy (Vòng Chung kết Smart Life)

> Vai: giám khảo khó tính, chấm theo ĐÚNG 6 tiêu chí mục III của
> `[Q-SmartEnergy] Khung Tiêu Chí Đánh Giá & AI Guidelines.md` (100 điểm).
> Phương pháp: đọc toàn bộ `backend/` + `client/src/`, chạy `pytest` (kết quả: **204/204 pass**,
> 14.4s). Chưa click demo trực tiếp bằng browser (không có công cụ browser trong phiên này) —
> các nhận định UX dựa trên đọc code render + luồng dữ liệu, có ghi rõ bước thao tác để tự kiểm chứng.

---

## 1. Bảng điểm dự kiến

| # | Tiêu chí (đúng tên rubric) | Trọng số | Điểm dự kiến | Lý do ngắn gọn |
|---|---|---|---|---|
| 1 | Tính năng & mức độ hoàn thiện | 25 | **19** | Nhiều tính năng chạy thật, 204 test pass, fallback không crash; TRỪ: thuật ngữ "Linh hoạt/Cố định" đảo ngược giữa 2 tab, ~4 file dead code, 1 endpoint không auth |
| 2 | Giải quyết vấn đề thực tiễn | 20 | **14** | QUBO ánh xạ ràng buộc thật rất tốt; TRỪ: baseline "trước" là kịch bản xấu nhất, solar 5kWp giả định bắt buộc cho mọi nhà, số ESG (CO₂/cây xanh) không có căn cứ |
| 3 | Chất lượng kỹ thuật | 15 | **13** | Điểm mạnh nhất: QUBO đúng toán, giải thích λ, warm-start greedy, bảng so sánh hyperparameter ngay trong UI, đối chiếu brute-force |
| 4 | Trình bày & thuyết phục | 15 | **8–9** | `docs/` TRỐNG — không có pitching script/slide/tài liệu QUBO nào trong repo; app có công cụ minh chứng tốt (bảng QAOA, Gemini explain) nhưng điểm mục này phụ thuộc hoàn toàn vào miệng người thuyết trình |
| 5 | Kết quả triển khai thực tế | 15 | **12** | Giá EVN 5 bậc + VAT 8% + biểu giá doanh nghiệp TOU đều là số thật có nguồn/quyết định; TRỪ: solar 525kWh/tháng "illustrative", catalog còn nhiều `[CẦN XÁC MINH]` |
| 6 | Giao diện & trải nghiệm UX/UI | 10 | **7** | UI đẹp, Gantt kéo-thả + ghost block, dark mode; TRỪ: lần tối ưu ĐẦU không có "trước/sau" trên Gantt, biểu đồ Insights kể một câu chuyện "trước" KHÁC với con số hóa đơn |
| | **Tổng** | **100** | **≈ 73–74** | Nền kỹ thuật giải nhất, nhưng phần "kể chuyện nhất quán" đang tự bắn vào chân |

---

## 2. Chi tiết lỗi / điểm yếu theo từng tiêu chí

Mức độ: 🟥 **Chặn điểm** (giám khảo thấy là trừ ngay) · 🟧 **Ảnh hưởng** (bị hỏi xoáy sẽ mất điểm) · 🟨 **Nhỏ nhặt**.

### ✅ Tiêu chí 1: Tính năng & mức độ hoàn thiện (25đ) — 5 vấn đề

**Điểm cộng trước:** auth Supabase JWKS chuẩn, phân quyền 3 role có test, matplotlib Agg thread-safe, mọi router chính đều bọc lỗi, `_error_figure` chống crash chart, 204 test pass — vượt yêu cầu "Try/Catch để demo không crash" của rubric.

1. 🟥 **Thuật ngữ "Linh hoạt / Cố định" bị ĐẢO NGƯỢC giữa các tab.**
   - Tab Thiết bị: `client/src/components/ApplianceManager.jsx:194` gắn nhãn nút **"Linh hoạt · theo nhu cầu"** cho thiết bị `is_flexible=false`, và `:198` **"Cố định · tự lên lịch"** cho `is_flexible=true` (xác nhận tại `:14`, `:57`, `:109-111`, `:131`, `:146`).
   - Tab Tối ưu: `client/src/pages/OptimizeTab.jsx:144-145` viết ngược lại: *"Tải linh hoạt: kéo khối để tối ưu lại. Tải cố định: bấm ô giờ để bật/tắt"* — ở đây "linh hoạt" = `is_flexible=true`.
   - Hướng dẫn: `client/src/pages/GuideTab.jsx:50-58` chép theo nhãn của tab Thiết bị, tức cũng ngược với tab Tối ưu và ngược với toàn bộ backend/README.
   - **Kịch bản lộ:** giám khảo mở tab Thiết bị thấy "Máy giặt" nằm dưới nút "Cố định", sang tab Tối ưu lại đọc "Tải linh hoạt: kéo khối" và kéo được đúng cái máy giặt đó. Một câu hỏi "vậy máy giặt là linh hoạt hay cố định?" là đủ vỡ trận.

2. 🟧 **~4 file dead code còn nguyên trong `client/src/`.** `pages/Dashboard.jsx`, `components/OptimizePanel.jsx`, `components/ResultsPanel.jsx`, `components/QuantumReactor.jsx` không được import bởi bất kỳ route nào trong `client/src/App.jsx:104-134` (route `/app/dashboard` dùng `InsightsTab`). Rubric III.1 yêu cầu "code dọn dẹp sạch sẽ" — giám khảo mở repo sẽ thấy 2 phiên bản Dashboard song song và không biết cái nào là thật.

3. 🟧 **`POST /api/alert` không có auth** — `backend/api/alert_router.py:15-16` không `Depends(get_current_user)` như mọi router khác. Ai biết URL đều dùng được server làm máy gửi email spam tới địa chỉ bất kỳ (khi `EMAIL_SENDER/PASSWORD` được cấu hình, `backend/api/alerts.py:53-57` gửi thật qua Gmail SMTP).

4. 🟨 **Tính năng gửi email cảnh báo chỉ tồn tại trong dead code.** `sendAlert` chỉ được gọi từ `components/ResultsPanel.jsx:118` (file không được route). Ngoài ra `client/src/api.js:83` gọi `POST /alert/` trong khi router prefix là `/api/alert` (`alert_router.py:6`) — nếu ai đó hồi sinh nút này, nó 404 ngay. Đừng nhắc đến "gửi email cảnh báo" khi pitch trừ khi nối lại.

5. 🟨 **Thư viện Gemini đã ngừng hỗ trợ.** `backend/api/explain_router.py:4` dùng `google.generativeai` — pytest in cảnh báo "All support for the google.generativeai package has ended". Không hỏng hôm nay, nhưng nếu giám khảo nhìn log server sẽ thấy warning.

### ✅ Tiêu chí 2: Giải quyết vấn đề thực tiễn (20đ) — 5 vấn đề

**Điểm cộng trước:** QUBO ánh xạ đúng và trung thực — H_cost/H_solar/one-hot/H_power viết rõ công thức kèm ý nghĩa kinh tế (`backend/core/qubo_builder.py:121-156`), tải nền cố định được cộng vào ràng buộc quá tải, business được tối ưu theo đúng biểu giá TOU mà bill tính (`optimize_router.py:195-204`).

1. 🟧 **Hóa đơn "trước" là kịch bản XẤU NHẤT, không phải thói quen thật.** `_worst_solar_schedule` (`backend/api/optimize_router.py:225-240`) đặt mỗi thiết bị linh hoạt vào giờ ÍT NẮNG NHẤT trong candidate_hours để làm baseline. "% tiết kiệm" vì vậy là *tiết kiệm so với trường hợp tệ nhất có thể* — một giám khảo tài chính sẽ gọi đây là thổi phồng. Code không giấu (đặt tên hàm là worst), nhưng UI ghi trần trụi "Hóa đơn trước" (`OptimizeTab.jsx:117`) không chú thích baseline là gì.

2. 🟧 **Mỗi nhà đều bị giả định có điện mặt trời 5kWp.** `backend/core/calc.py:50-51` hard-code `SOLAR_CAPACITY_KWP = 5`, `SOLAR_MONTHLY_GENERATION_KWH = 525` ("illustrative"); không có chỗ nào trong UI/DB cho user khai "tôi không có solar" hoặc đổi công suất. Toàn bộ giá trị tiết kiệm của trục H_solar dựa trên giả định này. Câu hỏi tất yếu: *"Nhà tôi không có pin mặt trời thì app còn tiết kiệm gì?"* — hiện tại chỉ còn trục tránh nhảy bậc, yếu hơn nhiều.

3. 🟧 **Số ESG là số chế.** `client/src/pages/InsightsTab.jsx:15-27`: "điện dời khỏi giờ cao" đếm mọi thiết bị linh hoạt không chạy lúc 17/18/19h — kể cả khi candidate_hours của nó (vd máy giặt 9h/14h) KHÔNG BAO GIỜ chứa 17-19h, tức "dời" một thứ chưa từng ở đó; CO₂ = kWh×0.8 rồi "cây xanh" = CO₂/22 không nguồn, và về vật lý *dời giờ chạy không giảm kWh tiêu thụ* nên không tự động giảm CO₂ (chỉ phần được solar hấp thụ mới giảm). Card "Tác động môi trường (ESG)" hiện to giữa trang Tổng quan — mồi câu hỏi xoáy hạng nặng.

4. 🟧 **Thiết bị cố định ngoài catalog bị dồn mặc định vào 18h (giờ đắt nhất).** `backend/core/appliance_catalog.py:122` `_DEFAULT_START_FALLBACK = 18`. Với tài khoản doanh nghiệp, MỌI thiết bị "theo nhu cầu" họ tự khai đều rơi vào cửa sổ bắt đầu 18h — đúng khung cao điểm TOU — làm cả bill trước/sau lẫn tải nền H_power méo theo một giả định vô hình mà user không được hỏi.

5. 🟨 **`quantity` gộp thành 1 khối:** `optimize_router.py:346` nhân `power_w × quantity` — 3 máy giặt buộc chạy CÙNG một giờ (một biến quyết định), và tổng công suất tức thời cũng x3. Chấp nhận được ở PoC nhưng phải nói được khi bị hỏi.

### ✅ Tiêu chí 3: Chất lượng kỹ thuật (15đ) — 4 vấn đề (đa số nhỏ)

**Điểm cộng trước:** đây là phần mạnh nhất. Chuỗi bằng chứng "hiểu tuning" đúng yêu cầu rubric III.3: λ=1e6 có giải thích trade-off landscape (`qubo_builder.py:200-209`), 4 cấu hình (reps, maxiter) đo runtime + so global optimum (`quantum_runner.py:187-242`) hiển thị ngay trong UI (`OptimizeTab.jsx:158-186`), warm-start bằng greedy (`quantum_runner.py:71-100`), SamplerV2 + transpile đúng recipe Qiskit mới, brute-force đối chiếu để demo không bao giờ trả nghiệm dưới tối ưu (`quantum_runner.py:353-360`).

1. 🟧 **QAOA không bao giờ được phép "thua nhưng vẫn được tính":** `QuantumScheduler.solve()` lấy nghiệm brute-force bất cứ khi nào nó tốt hơn (`quantum_runner.py:357-360`), nên badge `solver_used="qaoa"` chỉ xuất hiện khi QAOA trùng global optimum. Trung thực về mặt sản phẩm, nhưng suy ra: **mọi giá trị "lượng tử" của demo là chứng minh pipeline, không phải hiệu năng** — phải chủ động nói điều này trước khi bị hỏi (xem mục 3, câu Q1).

2. 🟨 **`/qaoa-analysis` chạy trên một QUBO KHÁC với `/optimize`:** `optimize_router.py:597` tạo `QuantumScheduler(flexible, profile)` không truyền `power_threshold_w`/`fixed_load_w` (và bỏ qua pin + duration_overrides), trong khi run thật có (`:426-428`). Năng lượng trong bảng phân tích vì vậy không so sánh được 1:1 với `energy` của run thật — nếu giám khảo tinh mắt đối chiếu 2 con số sẽ thấy lệch.

3. 🟨 **H_power chỉ xét giờ BẮT ĐẦU** — hai thiết bị chạy chồng lấn nhưng khác giờ bắt đầu không bị optimizer phạt (code tự ghi chú tại `qubo_builder.py:151-153`). Frontend có lưới an toàn hiển thị sau (`OptimizeTab.jsx:12-29` quét đủ 24h theo duration), nhưng đó là *phát hiện sau*, không phải *tránh trước*. Biết trả lời: "độ phân giải PoC theo giờ bắt đầu; cảnh báo runtime bắt phần còn lại".

4. 🟨 **Hai cách tính peak lệch nhau:** frontend `peakPower` dùng `Math.ceil(duration)` giờ tròn (`OptimizeTab.jsx:20`), backend `_hourly_load` dùng phần lẻ giờ (`optimize_router.py:139-144`) — thiết bị 0.5h bị frontend tính đủ 1h công suất. Có thể gây cảnh báo "Quá tải" giả trong demo với bình nóng lạnh 3500W × 0.5h.

### ✅ Tiêu chí 4: Trình bày & thuyết phục (15đ) — 3 vấn đề

1. 🟥 **`docs/` hoàn toàn trống.** Rubric III.4 nói rõ: *"sinh kịch bản thuyết trình (Pitching Script)"*. Trong repo không có script, không slide, không một trang giải thích QUBO cho người ngoài ngành. Toàn bộ 15 điểm mục này đang đặt cược vào trí nhớ của người thuyết trình sáng mai.

2. 🟧 **README hay nhưng bằng tiếng Anh** (`README.md`) — nếu ban giám khảo lướt repo, tài liệu chính không cùng ngôn ngữ với bài thi. Không chặn điểm, nhưng một trang tóm tắt tiếng Việt sẽ ăn điểm "câu chuyện tiết kiệm điện dễ hiểu".

3. 🟧 **Câu chuyện "trước/sau" không nhất quán giữa các màn hình** (chi tiết ở tiêu chí 6, mục 2) — đây là lỗi trình bày nhiều hơn là lỗi code: 3 nơi kể 3 baseline khác nhau.

### ✅ Tiêu chí 5: Kết quả triển khai thực tế (15đ) — 3 vấn đề

**Điểm cộng trước:** vượt yêu cầu "Data Generator sinh dữ liệu biểu giá điện thật của EVN": 5 bậc theo QĐ 1279/QĐ-BCT + VAT 8% có hiệu lực ghi rõ (`backend/core/calc.py:25-37`); biểu giá doanh nghiệp theo cấp điện áp + khung giờ QĐ 963 với quy ước làm tròn ranh giới viết hẳn vào docstring (`backend/core/business_calc.py:38-55`); thời tiết THẬT từ OpenWeatherMap 5 ngày (`backend/api/weather_router.py`), có cờ `forecast_available` để không im lặng giả định nắng.

1. 🟧 **Sản lượng solar là số minh họa:** 525 kWh/tháng "illustrative" (`calc.py:13,51`), đường cong Gauss sigma=3 quanh 12h (`data_prep.py:53-59`) — không dữ liệu bức xạ thật của VN. Khi bị hỏi "525 lấy đâu ra", câu trả lời hiện tại chỉ là "~105 kWh/kWp/tháng ước lệ".

2. 🟨 **Catalog thiết bị còn 7 chỗ `[CẦN XÁC MINH]`** ngay trong comment (`appliance_catalog.py:37,42,48,53,61,65,70,75,79`) — trung thực đáng khen, nhưng nếu giám khảo đọc code sẽ thấy chính tác giả chưa chốt số giờ dùng. Nguồn công suất thì có (Panasonic/Daikin/FPT Shop) — nhấn vào phần có nguồn.

3. 🟨 **Không mô hình bán điện dư (FIT/net-metering):** solar dư ngoài self-consumption coi như bỏ (`_bill_from_load`, `optimize_router.py:207-222`). Đây là lựa chọn bảo thủ hợp lý (cơ chế mua lại đang thay đổi) — nhưng phải nói được là *lựa chọn*, không phải *quên*.

### ✅ Tiêu chí 6: Giao diện & trải nghiệm UX/UI (10đ) — 4 vấn đề

**Điểm cộng trước:** rubric chỉ yêu cầu Streamlit/Gradio — team làm hẳn React + Supabase + role-based layout, Gantt kéo-thả có ghost "vị trí trước khi kéo" + chú thích tự hiện (`GanttEditor.jsx:186-192, 239-244`, CSS `App.css:221-227` đầy đủ), notification giờ bật/tắt thiết bị, dark mode.

1. 🟧 **Lần tối ưu ĐẦU TIÊN không có "trước vs sau" trên Gantt.** Ghost block chỉ xuất hiện khi lịch MỚI khác lịch NGAY TRƯỚC ĐÓ (`GanttEditor.jsx:29-42` so `schedule` với `prevScheduleRef`); lần bấm "Tối ưu hóa" đầu tiên (hoặc sau reload — rehydrate từ history rồi so với chính nó) không có gì để so → giám khảo xem demo lần đầu chỉ thấy MỘT lịch và hai con số tiền, không thấy *lịch trước trông thế nào*. Đây chính là điểm yếu đã biết; xác nhận vẫn đúng, và ghost-khi-kéo chỉ vá được kịch bản kéo tay. Rubric vòng ý tưởng từng yêu cầu "biểu đồ so sánh rõ ràng (không có Q-SmartEnergy) vs (có Q-SmartEnergy)".
   - **Cách hỏi vặn dễ gặp:** "Hóa đơn trước 2.1 triệu — chỉ cho tôi trên lịch này thiết bị nào đang chạy giờ nào mà ra 2.1 triệu?" → hiện không chỉ được trên Gantt.

2. 🟧 **Biểu đồ "Tải điện theo giờ" ở Tổng quan kể MỘT baseline khác với hóa đơn.** `client/src/components/BillChart.jsx:17-21` vẽ đường "Trước tối ưu" bằng cách cho mọi thiết bị linh hoạt chạy lúc **18h** ("dồn vào buổi tối"), trong khi backend tính `bill_before` theo giờ ÍT NẮNG NHẤT TRONG candidate_hours (máy giặt candidates 9h/14h → "trước" thật là 9h hoặc 14h, không bao giờ 18h). Hai màn hình cạnh nhau: chart nói "trước = 18h", tiền nói "trước = giờ ít nắng". Nếu giám khảo hỏi "đường cam này ứng với số tiền nào?", không có câu trả lời đúng.

3. 🟨 **Pie chart + area chart bỏ `quantity`:** `BillChart.jsx:50` tính kWh tháng không nhân `quantity`, trong khi tổng ở tab Thiết bị (`AppData.jsx:388-390`) và backend đều nhân. User có 2 điều hòa sẽ thấy 2 con số tổng khác nhau giữa 2 tab.

4. 🟨 **Duration override từ tab Dự báo áp âm thầm mãi mãi:** sau khi bấm "Chạy mô hình dự báo", `durationOverrides` (`AppData.jsx:258-260`) được đính vào MỌI lần optimize sau, không có chỗ nào trên tab Tối ưu hiển thị "đang dùng thời lượng dự báo X giờ" và không có nút xóa. Demo dễ rơi vào cảnh block Gantt dài khác với số giờ khai ở tab Thiết bị mà không ai giải thích được ngay.

---

## 3. Câu hỏi phản biện dự kiến + gợi ý trả lời

1. **"QAOA của các em có thắng được brute-force không? Nếu không thì lượng tử để làm gì?"** (chắc chắn bị hỏi)
   → Trả lời thẳng, đừng vòng vo: *"Ở quy mô PoC 4–5 qubit thì KHÔNG — 2⁵=32 tổ hợp, brute-force nhanh hơn và chắc chắn tối ưu; code chúng em tự ghi chú điều này (`optimize_router.py:434-437`) và `solve()` luôn đối chiếu brute-force để người dùng không bao giờ nhận nghiệm dưới tối ưu. Giá trị của QAOA ở đây là chứng minh TOÀN BỘ pipeline lượng tử chạy thật (QUBO → ansatz → Aer → decode), vì bài lập lịch là tổ hợp bùng nổ 2ⁿ: 20 thiết bị × 5 giờ ứng viên = 100 biến thì brute-force cần 2¹⁰⁰ tổ hợp — không máy cổ điển nào duyệt nổi, còn QAOA vẫn cho nghiệm xấp xỉ. Bảng 'Phân tích thuật toán lượng tử' trong app đo đúng trade-off đó."* Bấm nút phân tích NGAY trong demo để chủ động dẫn chuyện.

2. **"Hóa đơn 'trước' lấy từ đâu? Có phải các em chọn kịch bản xấu nhất để % tiết kiệm đẹp?"**
   → *"Baseline là 'người dùng bấm chạy thiết bị vào giờ bất lợi nhất TRONG CHÍNH khung giờ họ cho phép' — không phải một giờ tùy tiện ngoài thói quen của họ; hai hóa đơn dùng CÙNG lịch thiết bị cố định nên chênh lệch cô lập đúng giá trị của việc xếp lịch (docstring `_compute_schedule_bills`, `optimize_router.py:243-265`). Đúng là cận trên của tiết kiệm; kéo khối trên Gantt sang giờ bất kỳ sẽ thấy hóa đơn tính lại theo thời gian thực — số không bịa."* (Nếu kịp, thêm chú thích dưới chữ "Hóa đơn trước" — xem mục 4.)

3. **"Nhà không có điện mặt trời thì app này vô dụng?"**
   → Thừa nhận giới hạn: *"PoC hiện giả định hộ 5kWp (phân khúc mục tiêu: hộ tải cao đã lắp solar — nhóm đau ví nhất). Với hộ không solar, hệ vẫn còn trục tránh nhảy bậc giá + cảnh báo quá tải công suất; cho khai báo công suất solar (kể cả 0) chỉ là thêm 1 field — đã nằm trong roadmap."* Đừng để bị phát hiện là hard-code rồi mới thừa nhận.

4. **"Con số CO₂ giảm và 'tương đương cây xanh' lấy nguồn nào?"** (nếu họ thấy trang Tổng quan)
   → Hiện KHÔNG có nguồn và logic sai (dời giờ không tự giảm CO₂) — `InsightsTab.jsx:15-27`. Phương án tốt nhất: gỡ/sửa card này trước khi thi (mục 4). Nếu giữ và bị hỏi: *"Hệ số phát thải lưới điện VN ~0.72–0.8 kg CO₂/kWh (Bộ Công Thương công bố hằng năm); phần giảm thật là phần tải được dời vào giờ solar tự cấp — bọn em nhận là card này đang tính lạc quan và sẽ sửa."*

5. **"Máy giặt là tải 'linh hoạt' hay 'cố định'? Hai tab của các em nói ngược nhau."**
   → Không có câu trả lời đẹp — PHẢI SỬA LABEL TRƯỚC KHI THI (lỗi 🟥 số 1). Nếu lỡ bị hỏi khi chưa sửa: *"Nhãn ở tab Thiết bị đặt theo góc nhìn người dùng ('cố định' = hệ thống chốt giờ giúp bạn) và bọn em nhận đây là lỗi wording sẽ thống nhất lại"* — nhưng đây là câu chữa cháy, không phải câu trả lời.

6. **"EVN tính tiền theo THÁNG, sao app các em có 'giá theo giờ trong ngày'?"**
   → *"Đúng, VN không có giá điện sinh hoạt theo giờ. Chúng em mô hình GIÁ BIÊN: giả định tiêu thụ dàn đều, đến ngày thứ d trong tháng hộ đã tích lũy X kWh, nên kWh TIẾP THEO trong ngày hôm đó rơi vào một bậc cụ thể — 'nhảy bậc trong ngày' chính là tín hiệu optimizer cần (`data_prep.py:22-29`). Riêng khách doanh nghiệp thì có giá theo giờ thật (TOU 3 khung, QĐ 963) và app dùng đúng biểu giá đó."* — câu trả lời này ăn điểm II.2 nếu nói trơn tru.

7. **"Cao điểm là 17h30–22h30, sao code tính 18–22h?"**
   → *"App phân giải theo giờ nguyên; ranh giới lửng làm tròn theo đa số phút của giờ đó: giờ 17 đa số phút trước 17h30 → bình thường; giờ 22 đa số phút trước 22h30 → cao điểm. Quy ước ghi trong docstring `classify_hour_tou` (`business_calc.py:42-49`)."*

8. **"Hai thiết bị chạy CHỒNG GIỜ nhưng khác giờ bắt đầu có bị phát hiện quá tải không?"**
   → *"Trong QUBO thì chưa — H_power xét tại giờ bắt đầu (giới hạn PoC, ghi chú tại `qubo_builder.py:151-153`); nhưng lớp kiểm tra sau tối ưu trên UI quét đủ 24 giờ theo suốt thời gian chạy và hiện cảnh báo đỏ kèm tên thiết bị. Phòng thủ 2 lớp: tránh trước phần lớn, phát hiện sau phần còn lại."*

9. **"3 cái máy giặt (quantity=3) thì lịch chạy thế nào?"**
   → *"PoC gộp thành 1 khối power×3 chạy cùng giờ — giữ số qubit nhỏ. Tách mỗi máy 1 biến chỉ là nhân bản Appliance trước khi build QUBO, đổi 1 hàm (`_db_rows_to_appliances`)."*

---

## 4. Ưu tiên sửa trước 8h sáng mai

### 🟥 PHẢI sửa (30–60 phút tổng, rủi ro thấp, chặn được câu hỏi chết người)

1. **Đảo lại 2 nhãn nút ở `ApplianceManager.jsx:194,198` + sửa đoạn mô tả tương ứng trong `GuideTab.jsx:50-58`** cho khớp ngữ nghĩa backend (linh hoạt = tự lên lịch/kéo được; cố định = theo nhu cầu/bấm ô giờ). ~10 phút, chỉ đổi text, không đụng logic. Đây là lỗi rẻ nhất - sát thương cao nhất.
2. **Gỡ hoặc trung thực hóa card ESG** (`InsightsTab.jsx:93-98`): hoặc xóa card, hoặc đổi thành "kWh được solar tự cấp thêm × 0.72 kg/kWh (hệ số lưới VN)" tính từ dữ liệu thật. Gỡ là nhanh và an toàn nhất.
3. **Sửa caption/logic đường "Trước tối ưu" trong `BillChart.jsx`**: tối thiểu đổi chú thích `:62` thành "kịch bản minh họa: dồn tải vào 18h" để không mạo nhận là baseline của hóa đơn; tốt hơn là vẽ theo worst-solar candidate hour cho khớp backend.
4. **Viết 1 trang pitching script tiếng Việt vào `docs/`** (rubric III.4 yêu cầu đích danh): mở bài nỗi đau hóa đơn → demo 4 bước → chốt bảng QAOA + câu trả lời Q1/Q2/Q3 ở trên. Không cần đẹp, cần TỒN TẠI.

### 🟧 Nên sửa nếu còn thời gian

5. Thêm 1 dòng chú thích dưới "Hóa đơn trước" (`OptimizeTab.jsx:117`): *"= chạy các tải linh hoạt vào giờ bất lợi nhất trong khung cho phép"*.
6. Hiện badge "Đang dùng thời lượng dự báo" trên tab Tối ưu khi `durationOverrides` không rỗng + nút xóa (`AppData.jsx:258`).
7. Nhân `quantity` trong pie/area chart (`BillChart.jsx:22,29,50`).
8. Thêm `Depends(get_current_user)` vào `alert_router.py:16`.

### 🟨 Bỏ qua được (đừng đụng vào đêm trước khi thi)

- Xóa dead code (`Dashboard.jsx`, `OptimizePanel.jsx`, `ResultsPanel.jsx`, `QuantumReactor.jsx`) — muốn xóa thì xóa nguyên file, đừng refactor.
- `/qaoa-analysis` truyền thiếu threshold/fixed_load — chỉ cần biết để trả lời.
- Migrate `google.generativeai` → `google.genai`.
- H_power theo giờ bắt đầu, quantity gộp khối, FIT/export solar — trả lời miệng theo mục 3.
- Fallback 18h cho thiết bị lạ — tránh demo tài khoản business với thiết bị "theo nhu cầu" tự khai; nếu demo business, chỉ dùng thiết bị tự lên lịch.

---

## 5. Xác minh các claim từ phiên trước

- ✅ **Bug "Hóa đơn trước thổi phồng khi pin thiết bị ngoài catalog" ĐÃ SỬA và còn đúng:** snapshot `true_flexible_appliances` chụp trước khi pin (`optimize_router.py:377`), truyền xuống `_compute_schedule_bills(..., true_flexible=...)` (`:451-454`); regression test `tests/test_pinned_baseline.py` tái hiện cả hành vi buggy cũ lẫn hành vi đã fix, và toàn bộ **204 test pass**.
- ⚠️ **Điểm yếu Gantt "chỉ 1 lịch" ĐÃ VÁ MỘT NỬA:** ghost block + legend đã có (`GanttEditor.jsx:186-192,239-244`) nhưng chỉ kích hoạt khi kéo/tối ưu lại — lần tối ưu đầu tiên (kịch bản demo chính) vẫn không có hình ảnh "trước". Kết luận: **vẫn là điểm trừ thuyết phục**, xem tiêu chí 6 mục 1 và câu hỏi Q2. Lưu ý: các file `Dashboard.jsx`/`ResultsPanel.jsx` nêu trong context cũ là dead code — Gantt thật nằm ở `OptimizeTab.jsx` + `GanttEditor.jsx`.
