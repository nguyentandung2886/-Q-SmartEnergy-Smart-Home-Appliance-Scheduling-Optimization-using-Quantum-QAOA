# Báo cáo Audit Toàn diện — Q-SmartEnergy (2026-07-03)

> **Vai:** Kiến trúc sư kỹ thuật cấp cao kiêm Giám khảo mô phỏng, chấm theo đúng
> `[Q-SmartEnergy] Khung Tiêu Chí Đánh Giá & AI Guidelines.md`.
> **Phương pháp:** 4 luồng audit độc lập (Thuật toán QAOA/QUBO · Giá điện EVN · Nghiệp vụ backend ·
> UX/UI), đọc toàn bộ `backend/` + `client/src/`, đối chiếu ngược với `docs/judge_review.md`,
> xác minh biểu giá EVN online (có nguồn), và **tái hiện thật** các lỗi Critical bằng tính toán
> read-only (không sửa file nào).
>
> **Verification thực tế (không ép pass):**
> - `cd backend && pytest -q` → **207 passed / 0 failed**, 46 warnings, 21.16s. Warnings đáng chú ý:
>   `google.generativeai` đã ngừng hỗ trợ; Qiskit `NLocal`/`BlueprintCircuit` sẽ bị xóa ở Qiskit 3.0.
> - `cd client && npm run build` → **✓ built in 683ms, 0 lỗi**. Cảnh báo duy nhất: bundle JS
>   1.114 MB > 500 kB (nên code-split, không chặn demo).

---

## 1. Tóm tắt điều hành (Executive Summary)

**Kết luận một câu:** nền tảng kỹ thuật ở mức giành giải nhất — biểu giá EVN khớp 100% văn bản
hiện hành, toán QUBO đúng và trung thực, 207 test xanh, auth chuẩn — nhưng hệ thống chỉ vững
**bên trong đường bao demo**: có **4 lỗi Critical** (2 đã tái hiện được) khiến demo có thể
**crash 500, treo vô hạn, hoặc hiện hộp đỏ stack-trace giữa buổi chấm** nếu giám khảo nghịch
input. Tất cả đều sửa được trong ~2–3 giờ.

### Điểm ước lượng theo rubric

| Vòng | Điểm ước lượng | Ghi chú |
|---|---|---|
| **Vòng lên ý tưởng (mục I, /100)** | **≈ 82–83** | Mạnh nhất ở tính thực tiễn (giá EVN thật) + độc đáo (QAOA); mất điểm ở khả thi (không có trần qubit) và "so sánh trước/sau" chưa trọn trên Gantt |
| **Vòng phụ (mục II, điểm cộng)** | **Đủ điều kiện cả 3 mức (+8, +15, +25)** | Cảnh báo quá tải ✓, ML forecast thời lượng ✓, hybrid quantum-classical + solar trong hàm mục tiêu ✓ — nhưng claim "chạy mượt laptop" (II.3) chỉ đúng khi n nhỏ và **không được enforce** |
| **Vòng chung kết (mục III, /100)** | **≈ 76–77** | Chi tiết từng tiêu chí ở mục 6. Tăng ~3 điểm so với tự đánh giá cũ (73–74) nhờ đã fix nhãn Linh hoạt/Cố định, gỡ card ESG, viết xong pitching script — nhưng phát hiện thêm 4 Critical mà bản tự đánh giá bỏ sót |

### 4 lỗi Critical phải sửa trước ngày chấm

1. **[Client] Debug overlay + promise thiếu `.catch`** → hộp đỏ stack-trace tràn màn hình và
   **làm đơ toàn bộ React app** khi backend chậm 1 giây (`client/src/main.jsx:7-12`).
2. **[Quantum] QUBO infeasible công suất → HTTP 500** — đã tái hiện: thiết bị 6000W vượt ngưỡng
   5000W tại mọi giờ ứng viên → bitstring vi phạm one-hot → `ValueError` không ai bắt
   (`qubo_builder.py:116-117`, `quantum_runner.py:373`).
3. **[Quantum+Backend] Không có trần qubit/timeout** — brute-force 2ⁿ chạy **vô điều kiện** sau
   mỗi lần QAOA; ~8 thiết bị linh hoạt × 4 giờ = treo worker hàng giờ (`quantum_runner.py:357`).
4. **[Backend] `duration_overrides: "inf"` → vòng lặp vô hạn** trong `_hourly_load`
   (`optimize_router.py:141`) — treo worker bằng một request JSON.

### Đối chiếu `docs/judge_review.md` (bản tự đánh giá cũ)

- **Không phóng đại** về biểu giá, QUBO, test — các claim kỹ thuật đều xác minh đúng.
- **Đã lỗi thời (theo hướng tốt):** 3 việc 🟥 đã làm xong — nhãn Linh hoạt/Cố định đã đảo đúng
  (`ApplianceManager.jsx:292,296`), card ESG đã gỡ (`InsightsTab.jsx` còn 81 dòng),
  `docs/pitching_script.md` đã tồn tại và chất lượng tốt; caption "minh họa" đã thêm vào BillChart.
- **Bỏ sót nghiêm trọng:** cả 4 lỗi Critical ở trên đều **không có** trong bản tự đánh giá.

---

## 2. Thuật toán QAOA/QUBO

✅ Đã audit **Thuật toán QAOA/QUBO** — 9 phát hiện.

**Điểm cộng xác minh được:** lõi toán khớp chính xác giữa README ↔ docstring ↔ code (dấu, hệ số,
`min(E,S)`, khai triển one-hot bỏ hằng số, convention *upper-triangular* ↔ `xᵀQx` tại
`qubo_builder.py:192-194, 210-216`); kết quả giao ra luôn là *global optimum* của QUBO nhờ đối
chiếu brute-force; tiền hiển thị dùng biểu giá thật (`calc.calculate_bill`) — kiến trúc
"QUBO là heuristic tìm kiếm, bill là sự thật" là đúng đắn và tự khai báo hạn chế minh bạch.

### Q-C1 · [Critical] QUBO infeasible công suất → server crash 500 (đã tái hiện)

- **File:dòng:** `backend/core/qubo_builder.py:116-117` (λ1=λ2=1e6 bằng nhau tuyệt đối),
  `backend/core/quantum_runner.py:257-258, 373` (`decode_schedule` raise `ValueError`),
  `backend/api/optimize_router.py:437` (không catch).
- **Cơ chế:** khi một thiết bị linh hoạt có `power_w × quantity + F(h) > power_threshold_w` tại
  **mọi** candidate hour, đường chéo mỗi biến là `cost − λ1 + λ2 = cost > 0` (λ1, λ2 **triệt tiêu
  nhau chính xác**) → nghiệm toàn cục là **tắt hẳn thiết bị** (vi phạm one-hot / ràng buộc
  "chạy đúng một lần"). Brute-force (luôn chạy đối chiếu) trả bitstring vi phạm →
  `decode_schedule` raise → **HTTP 500 giữa demo**.
- **Tái hiện thật:** `Bếp từ đôi ×2 = 6000W`, candidates (11, 18), threshold mặc định 5000W →
  `bitstring: 0100, energy: −1000000.0, one-hot valid: False` → `ValueError`. Kịch bản rất thực
  tế vì `_db_rows_to_appliances` nhân `power_w × quantity` (`optimize_router.py:344`) và tải nền
  cố định dồn 18h có thể tự đẩy `F(h)` vượt ngưỡng.
- **Đề xuất:** (1) đặt `lambda_power < lambda_onehot` (vd `5e5`) — nghiệm one-hot hợp lệ "ít vi
  phạm nhất" luôn thắng nghiệm tắt thiết bị; (2) guard trong `_build_result`: bitstring không
  one-hot → HTTP 422 *"thiết bị X vượt ngưỡng công suất tại mọi giờ ứng viên"*.
- **Rubric:** II.3 (crash trước giám khảo), III.2 (ràng buộc ánh xạ sai ở biên).

### Q-C2 · [Critical] Không trần qubit, không timeout — input người dùng treo server vô hạn

- **File:dòng:** `backend/core/quantum_runner.py:357` (brute-force 2ⁿ chạy **vô điều kiện** kể cả
  khi QAOA thành công); `backend/api/appliances_router.py:16-31` (`power_w`/`quantity` không trần,
  `candidate_hours` không giới hạn độ dài, không dedupe); đã grep toàn backend — **không tồn tại**
  `MAX_QUBIT`/`timeout` nào.
- **Cơ chế:** n = Σ|candidate_hours| do user quyết định. 7 thiết bị × 4 giờ = 28 qubit →
  brute-force 2²⁸ ≈ 2,7×10⁸ vòng matmul → hàng chục phút; n ≳ 30 → Aer statevector nổ RAM →
  `QAOAExecutionError` → fallback brute-force 2ⁿ → **treo vĩnh viễn, worker uvicorn bị chiếm** —
  demo đứng hình, tệ hơn 500. Fallback hiện **chỉ** kích hoạt theo lỗi/one-hot invalid
  (`quantum_runner.py:344-351`), **không theo kích thước bài toán** — trả lời trực tiếp câu hỏi
  audit: *ngưỡng qubit cho fallback không tồn tại*.
- **Đề xuất:** chặn đầu `/optimize`: `if n_vars > 20 → HTTP 422`; bỏ bước brute-force đối chiếu
  khi n > 20; validator `candidate_hours`: dedupe + `max_length=6`.
- **Rubric:** II.3 — "chạy mượt trên laptop thường" chỉ đúng có điều kiện (n ≤ ~15) mà điều kiện
  không được enforce.

### Q-H1 · [High] Claim "λ=1e6 không bao giờ bị mua lại" sai với input hợp lệ của API (đã tái hiện)

- **File:dòng:** `README.md:163-165` ("can **never** be bought back"),
  `qubo_builder.py:203-209` ("KHÔNG BAO GIỜ đánh đổi").
- **Tính toán:** cost term = `E_i·P(h)`; ngưỡng "mua lại" là `E_i ≳ 252 kWh/lần chạy` (ở bậc 5
  = 3.967đ). Ví dụ đề bài: 5000W × 8h × 3.967đ ≈ 158.680đ — an toàn (λ gấp ~6 lần). Nhưng
  `power_w`, `quantity` **không có trần**: 15.000W (quantity=5) × 24h = 360 kWh → cost ≈
  1.077.000đ > 1e6 → tái hiện được `one-hot valid: False` → dẫn thẳng về crash Q-C1. Vậy 1e6
  đúng cho **demo/catalog**, không đúng "với mọi dữ liệu" như README khẳng định.
- **Đề xuất:** λ động: `lam = max(1e6, 10 × max(E_i) × P_max)`; hoặc trần validate
  `power_w ≤ 20000`, `quantity ≤ 10`; sửa chữ "never" trong README.
- **Rubric:** III.2, III.3 (giám khảo hỏi *"1e6 lấy đâu ra, chứng minh đủ lớn?"* sẽ lộ).

### Q-M1 · [Medium] README mô tả H_power THIẾU so với code (code đúng hơn README)

`README.md:157` chỉ ghi thành phần cặp `x_{i,k}·x_{i',k'}` — thiếu (a) thành phần **đường chéo**
một-thiết-bị-tự-vượt-ngưỡng và (b) tải nền cố định `F(h)` trong cả hai điều kiện. Code có đủ
(`qubo_builder.py:224-226` diagonal + `:230-238` cặp); docstring `qubo_builder.py:128-130` đúng.
→ Cập nhật README khớp docstring. Các term còn lại **khớp chính xác 100%**. — *Rubric III.2.*

### Q-M2 · [Medium] H_cost/H_solar chỉ nhìn GIỜ BẮT ĐẦU cho thiết bị chạy nhiều giờ — không được khai báo

`qubo_builder.py:190-194`: toàn bộ `energy_kwh` bị định giá `P(start)` và solar credit
`min(E, S(start))` — máy giặt 2h chạy 11h–13h thực nhận solar của cả 3 giờ; giá biên có thể nhảy
bậc giữa ngày (`data_prep.py:82-85`). Bill hiển thị (`_compute_schedule_bills`) lại trải tải
từng giờ → objective QUBO và tiền thật đo hai thứ khác nhau khi duration > 1h. Hạn chế tương tự
của H_power được tự khai (`qubo_builder.py:151-153`), hạn chế này thì **im lặng** → giám khảo
kỹ thuật dễ bắt. Tối thiểu: ghi chú vào docstring + README. — *Rubric III.2.*

### Q-M3 · [Medium] Bằng chứng "QAOA đạt global optimum" yếu về phương pháp

`quantum_runner.py:187-242` (`compare_qaoa_hyperparameters`, seed=42) + `:165,178`
(`SamplerV2` 1024 shots, chọn mẫu đo tốt nhất): với 4–6 qubit chỉ có 16–64 trạng thái — 1024
shots của **cả mạch ngẫu nhiên** cũng phủ gần hết → `matches_global_optimum=True` gần như luôn
xảy ra, **không phân biệt** config tốt/tệ. Không phải gian lận (đối chiếu brute-force là thật),
nhưng câu bẻ *"tắt optimizer đi có còn ra optimum không?"* — trả lời hiện tại là "vẫn ra".
→ Thêm cột **xác suất đo được nghiệm tối ưu** (tỉ lệ shots trúng bitstring optimum) — chỉ số này
mới phân biệt reps/maxiter và biến bảng thành bằng chứng tuning thật. — *Rubric III.3.*

### Q-M4 · [Medium] "Warm-start" không phải warm-start QAOA chuẩn, và bảng phân tích không dùng nó

`quantum_runner.py:169-177`: initial state = |greedy⟩ bằng cổng X — basis state là eigenstate
của H_C nên layer cost đầu chỉ tạo global phase; kỹ thuật chuẩn (Egger et al.) dùng RY rotation
+ mixer tương thích. Nên gọi là *"greedy-seeded initial state"* khi pitch. Quan trọng hơn:
run thật có warm-start, `compare_qaoa_hyperparameters` (`:221`) thì **không** → hai kết quả
không so 1:1 được. — *Rubric III.3.*

### Q-L1 · [Low] `/qaoa-analysis` xây QUBO khác `/optimize` — lệch nhiều hơn judge_review đã ghi

`optimize_router.py:588-595`: thiếu `_coerce_unoptimizable_to_fixed`, thiếu
`power_threshold_w`/`fixed_load_w`, thiếu business TOU profile, bỏ pinned + duration_overrides
→ `energy`/`num_variables` trong bảng phân tích không khớp run thật. — *Rubric III.3.*

### Q-L2 · [Low] Bảng edge case (trả lời đầy đủ câu hỏi audit)

| Case | Kết quả | File:dòng |
|---|---|---|
| (a) 0 thiết bị linh hoạt | Không crash — QAOA lỗi trên QP 0 biến → fallback trả bitstring rỗng, schedule `{}`; chỉ nhiễu cosmetic `used_fallback=True` | `quantum_runner.py:59-68, 245-251` |
| (b) 1 candidate hour | `/optimize` coerce thành fixed — đúng; `/qaoa-analysis` không coerce nhưng one-hot 1 biến ép x=1, không crash | `optimize_router.py:316-327` |
| (c) mọi giờ đều vượt công suất | **CRASH 500** — xem Q-C1 | `quantum_runner.py:373` |
| (d) candidate_hours rỗng + is_flexible | `/optimize` coerce OK; gọi `build_qubo` trực tiếp: thiết bị "biến mất" im lặng | `qubo_builder.py:167-177` |
| (e) duplicate candidate hours | Không crash nhưng phí qubit (không dedupe) → liên đới Q-C2 | `appliances_router.py:24-31` |

**Thời gian chạy (câu hỏi II.3):** mặc định reps=1, maxiter=50, shots=1024, COBYLA
(`quantum_runner.py:104-110, 296-297`); demo household 3 thiết bị × 2 giờ = 6 qubit → ~1–5s/solve,
`/qaoa-analysis` 4 config ~10–40s → **đạt** "chạy mượt laptop thường". Nhưng không có gì bảo vệ
điều kiện đó (Q-C2).

**Điểm ước lượng:** III.2 = **14/20** · III.3 = **11/15**.

---

## 3. Tuân thủ giá điện EVN

✅ Đã audit **Tuân thủ giá điện EVN** — 6 phát hiện (1 Medium, 5 Low). **Đây là phần chắc nhất
của toàn dự án — biểu giá khớp 100% văn bản hiện hành, có nguồn xác minh online ngày 03/07/2026.**

### Bảng đối chiếu CODE vs THỰC TẾ (xác minh online 03/07/2026)

| Hạng mục | Trong code | Thực tế hiện hành | Kết luận |
|---|---|---|---|
| Sinh hoạt 5 bậc, chưa VAT (`calc.py:57-65`) | 1.984 / 2.380 / 2.998 / 3.571 / 3.967 đ/kWh (0–100/200/400/700/>700) | Y hệt — QĐ 1279/QĐ-BCT áp dụng từ 10/5/2025, **chưa có điều chỉnh mới nào tính đến 7/2026** | ✅ Khớp 100% |
| Kinh doanh <6kV (`business_calc.py:23-35`) | 3.152 / 1.918 / 5.422 (bình thường/thấp/cao điểm) | Y hệt; 5.422đ xác nhận là mức cao nhất toàn biểu | ✅ Khớp |
| Kinh doanh ≥22kV, 6–22kV; sản xuất 4 cấp điện áp | 2.887/1.609/5.025; 3.108/1.829/5.202; SX 1.811→3.640 | Khớp bảng QĐ 1279 (spot-check nhiều mức) | ✅ Khớp |
| Khung giờ TOU (time-of-use) (`classify_hour_tou`, `business_calc.py:38-55`) | 0–5 thấp điểm, 18–22 cao điểm, còn lại bình thường; mọi ngày như nhau | **QĐ 963/QĐ-BCT (22/4/2026)**: 00–06 thấp; cao điểm 17h30–22h30 **T2–T7**; **Chủ nhật không có cao điểm** | ⚠️ Khớp trừ Chủ nhật + quy ước làm tròn giờ lửng (đã ghi docstring) |
| VAT | 8%, cộng đúng 1 lần, single-source (`business_calc.py:19` import từ calc) | 8% cho điện, hiệu lực 01/7/2025–31/12/2026 (NQ 204/2025/QH15 + NĐ 174/2025) | ✅ Khớp (lưu ý hết hạn 31/12/2026) |
| Solar 5kWp / 525 kWh/tháng (`calc.py:50-51`), Gauss σ=3 (`data_prep.py:53-59`) | Tự khai "illustrative", không nguồn | ~1.260 kWh/kWp/năm nằm trong dải hợp lý VN (Bắc ~950–1.100, Nam ~1.300–1.500) | ⚠️ **[CẦN XÁC MINH THỦ CÔNG]** theo địa điểm (đề xuất dẫn PVGIS / Global Solar Atlas) |

**Lưu ý quan trọng cho phản biện:** khung "cao điểm 9h30–11h30 & 17h–20h" là khung **CŨ**
(TT 16/2014/TT-BCT) — đã bị QĐ 963/QĐ-BCT thay thế từ 22/4/2026. Code đang theo khung **mới** —
nếu giám khảo hỏi theo khung cũ, đây là điểm ăn thêm, không phải lỗi.

### Phát hiện

1. **[Medium] E-M1 — Không xử lý Chủ nhật trong TOU doanh nghiệp.** `business_calc.py:43-44`
   tự khai "mọi ngày coi là ngày thường"; `_load_by_tou_period` (`optimize_router.py:161-168`)
   nhân thẳng ×30 ngày. Theo QĐ 963, ~4–5 Chủ nhật/tháng khung 17h30–22h30 phải tính giá bình
   thường → kWh cao điểm bị tính **thừa ~14%** (bill business hơi cao cả trước lẫn sau, savings%
   méo ít). *Sửa tối thiểu:* nhân phần cao điểm với 26/30, dồn 4/30 vào bình thường; ghi rõ giả
   định khi pitch. — *Nguồn: QĐ 963/QĐ-BCT.*
2. **[Low] E-L1 — Comment ngày hiệu lực lệch:** `calc.py:26` ghi "hiệu lực từ 29/05/2025" —
   thực tế **giá theo QĐ 1279 áp dụng từ 10/5/2025**; 29/5 là hiệu lực QĐ 14/2025/QĐ-TTg (văn
   bản cơ cấu 5 bậc). Số tiền không sai, chỉ sửa chú thích.
3. **[Low] E-L2 — Không làm tròn về đồng nguyên** (float thô) — hóa đơn EVN thật làm tròn đến
   đồng; sai khác <1đ, chỉ là hiển thị.
4. **[Low] E-L3 — `VAT_RATE=0.08` hardcode không kèm hạn:** từ 01/01/2027 phải trả về 10% nếu
   không gia hạn — nên để TODO kèm ngày.
5. **[Low] E-L4 — `_estimate_user_monthly_kwh` lệch với billing thật:**
   `optimize_router.py:330-335` ước kWh tháng = Σ power×duration×30, trong khi thiết bị cố định
   được bill theo giờ ON trong `usage_windows` (`:145-157`) → bậc giá biên trong QUBO có thể lệch
   bậc so với bill thật. Chỉ ảnh hưởng chất lượng heuristic, **không ảnh hưởng số tiền hiển thị**.
6. **[Low] E-L5 — Catalog thiết bị còn các chỗ `[CẦN XÁC MINH]`** trong comment
   (`appliance_catalog.py:37-79`) — trung thực nhưng giám khảo đọc code sẽ thấy; nguồn công suất
   (Panasonic/Daikin/FPT Shop) thì có — nhấn vào phần có nguồn.

**Xác nhận sạch (trả lời câu hỏi audit):** README "hộ gia đình không TOU" — **không lẫn logic
business sang household**: `_business_billing_params` trả `None` cho user thường
(`optimize_router.py:171-190`); `P(h)` household thay đổi theo giờ là **giá biên theo tích lũy
tháng** (marginal price), giải thích nhất quán ở `data_prep.py:22-29` + README:172-194, và hóa
đơn hiển thị **không dùng** P(h) — chỉ QUBO dùng làm heuristic. Test
`test_household_profile_price_is_tiered_not_tou` khóa regression này. VAT không cộng 2 lần,
không quên; đơn vị kWh/VNĐ nhất quán. Solar dư **không** bán (không FIT) — lựa chọn bảo thủ có
chủ đích, làm bill không bị tính thấp đi.

**Nguồn đối chiếu:** EVN (Biểu giá theo QĐ 1279/QĐ-BCT) · EVN + ThuVienPhapLuat (QĐ 963/QĐ-BCT
2026 về khung giờ) · LuatVietnam (bảng giá điện sinh hoạt 2026) · ThuVienPhapLuat (NQ 204/2025/QH15
VAT 8% đến 31/12/2026) · VietnamNet (khung giờ cao điểm mới, 5.422 đ/kWh).

**Điểm ước lượng:** III.5 = **12,5–13/15** (trừ: solar minh họa không nguồn −1; bỏ Chủ nhật
−0,5~1; catalog [CẦN XÁC MINH] −0,5).

---

## 4. Nghiệp vụ hệ thống (Backend)

✅ Đã audit **Nghiệp vụ hệ thống** — 12 phát hiện.

**Điểm cộng xác minh được:** auth JWKS **chắc chắn** — verify signature (ES256/RS256), audience
`"authenticated"`, issuer, expiry, leeway 120s, cache JWKS (`auth.py`) — không thấy lỗ hổng;
phân quyền admin đúng (`_resolve_role` chỉ tin `app_metadata`, ép `admin` giả trong
`user_metadata` xuống `household`, chặn ở backend không chỉ ẩn UI); **không có IDOR**
(appliances/schedules/feedback-me đều lọc `id AND user_id`); try/except đúng chỗ — QAOA fallback,
chart `_error_figure`, Gemini/OWM/SMTP đều suy giảm êm (degrade gracefully); Pydantic đã chặn
`power_w>0`, `duration (0,24]`, `quantity≥1`, `candidate_hours 0–23`, `day_of_month 1–30`.

### Phát hiện

1. **[Critical] B-C1 — `/optimize` treo vô hạn khi nhiều thiết bị linh hoạt** — trùng khớp độc
   lập với Q-C2 (2 luồng audit cùng tìm ra): `optimize_router.py:437` → `quantum_runner.py:357`
   brute-force 2ⁿ luôn chạy, không giới hạn số biến. Kịch bản: 8 thiết bị × 4 giờ = 32 biến →
   Aer nổ RAM → fallback 2³² ≈ 4 tỷ vòng → worker chết, **demo đứng hình**.
2. **[Critical] B-C2 — `duration_overrides` nhận `inf` → vòng lặp vô hạn.**
   `OptimizeRequest.duration_overrides: Dict[str, float]` (`optimize_router.py:79`, `:504`) không
   ràng buộc — Pydantic coerce chuỗi `"inf"` thành `float('inf')`, check `> 0` (`:366`) vẫn pass
   → `_hourly_load` (`:141`) `while remaining > 1e-9` không bao giờ dừng → **treo worker bằng 1
   request JSON**. NaN thì lọt thành bill NaN. *Sửa:* validator `0 < v ≤ 24` + `math.isfinite`.
3. **[High] B-H1 — `POST /api/alert` thiếu auth** (xác nhận lại từ judge_review, **vẫn còn**):
   `alert_router.py:15-16` không `Depends(get_current_user)` — ai có URL đều bơm email qua Gmail
   SMTP tới địa chỉ bất kỳ khi `EMAIL_SENDER/PASSWORD` cấu hình (`alerts.py:53-57`).
4. **[High] B-H2 — Pin `hour` ngoài 0–23 ở `/optimize` có thể 500.** `/recompute-bill` có check
   `0<=hour<=23` (`:543`) nhưng nhánh pin của `/optimize` (`:386`) chỉ validate khi appliance
   **có** candidate_hours; thiết bị candidate rỗng + pin `hour=25` → lọt vào `build_qubo._lookup(25)`
   → `ValueError` → 500. Không nhất quán giữa 2 router. *Sửa:* thêm cùng check vào `/optimize`.
5. **[High] B-H3 — Migration `appliances.quantity` thiếu `server_default`.**
   `0001_initial_schema.py:41` tạo cột NOT NULL không server_default; `models.py:66` `default=1`
   chỉ là Python-side. Code đã phòng thủ `row.quantity if row.quantity else 1` — chứng tỏ lường
   trước dữ liệu cũ có thể NULL/0. **[CẦN XÁC MINH THỦ CÔNG]**: DB production có cột `quantity`
   không (nếu được tạo từ phiên bản `0001` cũ hơn). *Đề xuất:* migration thêm `server_default="1"`
   — **hỏi trước khi đổi schema** theo ràng buộc audit.
6. **[High] B-H4 — `/qaoa-analysis` bỏ qua nhiều thứ hơn judge_review đã ghi:** ngoài thiếu
   threshold/fixed_load, còn thiếu `_coerce_unoptimizable_to_fixed` và business TOU profile
   (`optimize_router.py:588-595`) → `num_variables`/`energy` không so 1:1 với run thật.
7. **[Medium] B-M1 — `GET /feedback` trả feedback của MỌI user** cho bất kỳ user đăng nhập
   (`feedback_router.py:74-80`, có chủ đích theo docstring) và lộ `customer_name` — rò rỉ thông
   tin nhẹ, không phải IDOR ghi. Cân nhắc thu về `/feedback/me` + `/feedback/public`.
8. **[Medium] B-M2 — `POST /weather` không auth** (`weather_router.py:70`) — endpoint public gọi
   OpenWeatherMap trả phí, tốn quota key. Lỗi mạng đã bắt nên không crash.
9. **[Medium] B-M3 — Không có index cho `user_id`** trên appliances/schedules/feedback/
   business_profiles (cả models lẫn migrations) — mọi query nóng full-scan; demo thì bỏ qua được.
10. **[Low] B-L1 — `WeatherRequest.lat/lon` không giới hạn dải** (−90..90 / −180..180) — chỉ làm
    OWM trả rỗng → "sunny", không crash.
11. **[Low] B-L2 — Filter chống prompt-injection của `/explain` yếu** (`explain_router.py:85`):
    regex chặn từ khóa, bypass dễ, và chỉ chặn `payload.appliances` không chặn `schedule` — không
    gây crash, ghi nhận để trả lời nếu bị hỏi.
12. **[Low] B-L3 — `admin_router.get_stats` (`:66`):** role lạ vẫn tính vào `total_users` nhưng
    không hiện trong `users_by_role` → tổng con có thể ≠ tổng cha. Nhỏ.

**Alembic vs models.py (kiểm tra, không chạy migration):** cộng dồn 0001→0007 khớp models trừ
2 điểm ở B-H3 và B-M3. Khớp đúng: `users.role` server_default "household" (0004),
`business_profiles` + `voltage_level` (0004+0006), `feedback.is_featured` (0005),
`schedules.fixed_windows_json` (0002), `appliances.group_name` (0007).

**Nhất quán giữa router (trả lời câu hỏi audit):** đường tính bill **dùng chung**
`_compute_schedule_bills`/`_bill_from_load` → cùng lịch cho cùng số tiền giữa `/optimize` và
`/recompute-bill` ✅; `duration_overrides` xử lý y hệt ở 2 endpoint ✅; lệch duy nhất là
`/qaoa-analysis` (B-H4) và pin-hour validation (B-H2).

**Kết luận "demo có bao giờ crash?":** với đường demo chuẩn (household, thiết bị catalog) —
**rất chắc**. Nhưng 3 lối treo/500 tồn tại nếu nghịch input: duration `"inf"`, nhiều thiết bị
linh hoạt, pin hour ngoài 0–23. Cả ba nằm sau auth nên rủi ro là "giám khảo nghịch", không phải
public internet.

**Điểm ước lượng:** III.1 ≈ **20–21/25**.

---

## 5. UX/UI

✅ Đã audit **UX/UI** — 20 phát hiện.

**Bối cảnh quan trọng:** UI đã redesign sang phong cách "minimalist editorial" — palette thực tế
là **Teal #0F766E** (light) / #2DD4BF (dark); **Indigo #3730A3 / Gold #CA8A04 không còn dùng
trong app chính** (Landing là dark neon riêng). Câu hỏi contrast của đề bài được đo trên palette
thật. Contrast ratio dưới đây **đo bằng script**, không ước lượng.

### Phát hiện chính (ảnh hưởng demo)

1. **[Critical] U-C1 — Debug overlay toàn cục = quả bom lớn nhất cho demo.**
   `client/src/main.jsx:7-12`: `window.onerror` + `unhandledrejection` chèn
   `document.body.innerHTML += <div đỏ + stack trace>`. Trong khi đó `History.jsx:14`,
   `FeedbackTab.jsx:14`, `ProfileTab.jsx:23-26` gọi API **không có `.catch()`**, và
   save-on-blur ở Appliances ném lỗi lên không ai bắt. Backend chậm/rớt mạng 1 giây khi mở tab
   Lịch sử/Góp ý → **hộp đỏ stack-trace tràn màn hình trước giám khảo**, và vì `innerHTML +=`
   re-parse toàn bộ body nên **mọi event listener của React chết — app đơ hoàn toàn, phải F5**.
   *Sửa (~10'):* xóa 2 handler (hoặc chỉ `console.error`) + thêm `.catch()` cho 3 chỗ.
   *Ảnh hưởng demo:* một lần lag mạng = mất điểm III.1 "demo không crash" ngay tại chỗ.
2. **[High] U-H1 — Landing page: 6 biến CSS không tồn tại → animation "Peak Shaving" mất cột
   đỉnh tải.** `Landing.jsx:315` dùng `var(--error)`, `--neon-cyan`, `--neon-emerald`,
   `--neon-purple`, `--quantum-glow` — không định nghĩa ở đâu (`.landing-page` App.css:247-263
   chỉ có `--quantum`, `--energy`…) → cột val>70 (chính thứ cần "san phẳng") **không render**;
   số "Tiết kiệm VNĐ/tháng" của ROI calculator mất màu (`:254-257`); icon "4 Bước" mất nền tròn
   (`:358`). *Sửa (~5'):* thêm 5 biến vào block `.landing-page`.
3. **[High] U-H2 — GuideTab mô tả SAI tab "Dự báo":** `GuideTab.jsx:71-75` viết "dự báo thời
   tiết theo vị trí", nhưng `ForecastTab.jsx:12-16` là **dự báo thời lượng chạy bằng ML hồi quy**.
   Thêm: `:46-47` nhắc "nút gạt ở cột Loại" — cột không còn tồn tại; `:51-52` nói nhập "số giờ
   dùng/ngày" — form hiện không có ô đó. Giám khảo đọc Hướng dẫn rồi mở tab sẽ thấy 2 thứ khác nhau.
4. **[High] U-H3 — Ô candidate-hours trên Gantt gần như VÔ HÌNH khi trình chiếu:**
   `.gantt-cell-valid` (App.css:210) contrast **1,15:1**; khối ON cố định `.gantt-cell-on`
   (App.css:214) **2,34:1** (< 3:1 chuẩn non-text); ghost block nét dashed 1.5px opacity 0.6.
   Máy chiếu làm nhạt thêm → giám khảo **không nhìn thấy "khung giờ được phép kéo vào"** — đúng
   cái cần thấy để hiểu rubric I.4. *Sửa:* đậm `--accent-soft` riêng cho Gantt, cell-on lên 75%
   alpha, ghost 2px.
5. **[High] U-H4 — Lỗi mạng khi recompute bị NUỐT IM LẶNG → lịch trên màn ≠ số tiền.**
   `AppData.jsx:331-333` `catch { /* keep previous bill */ }` — bật thêm giờ thiết bị cố định,
   Gantt đổi ngay (optimistic) nhưng bill giữ số cũ, không toast. Kéo khối mà `runOptimize` fail
   (`AppData.jsx:298-299`): lỗi hiện ở card phía trên nhưng khối **vẫn nằm chỗ vừa kéo**
   (localSchedule không revert). *Sửa:* revert + hiện lỗi ngay dưới Gantt.
6. **[High] U-H5 — SSE Gemini:** `api.js:147-158` không check `response.ok` — backend trả
   401/500 → **không hiện gì cả**, như chưa bấm; stream đứt giữa chừng → `AppData.jsx:382`
   **ghi đè** text đang đọc dở bằng "Không thể kết nối Gemini." *Sửa:* throw khi !ok; catch thì
   nối "[Kết nối gián đoạn]" thay vì ghi đè.
7. **[High] U-H6 — Lần tối ưu ĐẦU vẫn không có "trước/sau" trên Gantt** (xác nhận điểm cũ còn
   đúng): `GanttEditor.jsx:29-42` chỉ so với schedule ngay trước trong phiên; lần đầu/sau reload
   không có ghost. Bill-strip + bar chart VNĐ có bù lại một phần, nhưng trên Gantt giám khảo chỉ
   thấy MỘT lịch — đụng thẳng yêu cầu I.5 "so sánh không có vs có Q-SmartEnergy".
8. **[Medium] U-M1 — BillChart baseline 18h vẫn khác backend — đã vá một nửa:** logic hardcode
   dồn 18h còn (`BillChart.jsx:17-21`) nhưng caption "kịch bản minh họa… KHÔNG phải baseline tính
   hóa đơn" đã thêm (`:62`). Giám khảo tinh ý vẫn hỏi "đường cam ứng với số tiền nào?" → "không
   số nào".
9. **[Medium] U-M2 — BillChart bỏ `quantity` + duration sai cho thiết bị cố định:**
   `BillChart.jsx:13,21-23,28-31,50` không nhân quantity (backend và tab Thiết bị có nhân —
   `AppData.jsx:388-390`); pie dùng `duration_hours` trong khi thiết bị "theo nhu cầu" luôn tạo
   với 1.0h → **tủ lạnh 24h hiển thị như chạy 1h/ngày**; 2 tab ra 2 tổng khác nhau.
10. **[Medium] U-M3 — Duration override từ tab Dự báo áp âm thầm vĩnh viễn** (còn nguyên):
    `AppData.jsx:258-260` đính vào mọi lần optimize, không badge/nút gỡ trên tab Tối ưu.
11. **[Medium] U-M4 — Chữ quá nhỏ cho máy chiếu:** header giờ Gantt 0.62rem ≈ 10px
    (App.css:204), th 0.68rem, bill-label 0.78rem — hàng số giờ 0–23 (thứ giám khảo cần đọc để
    hiểu "dời sang 11h trưa nắng") không đọc nổi ở 720p phòng lớn.
12. **[Medium] U-M5 — Contrast dưới chuẩn AA (đo thật):** stroke amber #F59E0B trên trắng
    **2,15:1** và cyan #06B6D4 **2,43:1** (2 đường chính của chart VNĐ trước/sau —
    `BillChart.jsx:69-85`); axis #9b9b9b **2,78:1**; text-muted #787774/#f7f6f3 **4,14:1** (sát
    ngưỡng, máy chiếu kéo xuống ~3,5). Đạt tốt: teal/trắng 5,47; dark mode ≥6,9. *Sửa nhanh:*
    stroke `#B45309`/`#0E7490`, axis `#6b6b6b`.
13. **[Medium] U-M6 — Hai ngôn ngữ thiết kế đối chọi:** Landing dark-neon chữ Anh ("Initialize
    Engine") vs app editorial sáng tiếng Việt — cú "gãy" thẩm mỹ ngay đầu demo. Không sửa rẻ
    được → cân nhắc **demo bắt đầu từ /login**.
14. **[Medium] U-M7 — Kéo-thả không hỗ trợ touch, không undo:** HTML5 Drag & Drop
    (`GanttEditor.jsx:59-96`) không chạy trên màn cảm ứng; `handleDrop` pin **tất cả** thiết bị
    linh hoạt (không chỉ cái vừa kéo), cách gỡ duy nhất là bấm lại "Tối ưu hóa" — không ai nói
    cho user. Trên laptop chuột thì mượt: hover highlight, debounce 400ms, trạng thái
    `reoptimizing` mờ Gantt.
15. **[Low] U-L1…L7:** màu lỗi dùng teal thay đỏ ở Feedback/Profile/Admin; `var(--indigo)`,
    `var(--error)` không định nghĩa ở `DevicesTab.jsx:44`, `ExplainSection.jsx:27`,
    `ApplianceManager.jsx:342` (mất màu đỏ cảnh báo khung giờ); CSS mồ côi (`time-scanner`,
    `.esg-row`…); nút ErrorBoundary dùng class không tồn tại; mật khẩu Register ≥8 vs Profile ≥6;
    5 chỗ gọi `getMe()` riêng lẻ + màn trắng nhấp nháy khi F5; bảng History không có wrapper
    overflow (chỉ vỡ <900px — máy chiếu 1280×720/1920×1080 **an toàn**, Gantt có overflow-x).

**Dead code (rubric III.1 "clean code"):** 4 file cũ (`pages/Dashboard.jsx`,
`components/OptimizePanel.jsx`, `ResultsPanel.jsx`, `QuantumReactor.jsx`) **+ 3 file mới phát
hiện** (`TiltCard.jsx`, `AnimatedBackground.jsx`, `useCountUp.js`) — 7 file không được route/import.

**Luồng UX theo rubric I.4 (điểm cộng lớn):** đăng nhập → thêm thiết bị → kết quả chỉ ~5 click
+ 1 form, và **thêm thiết bị tự động chạy tối ưu luôn** (`ApplianceManager.jsx:237`) — rất đúng
tinh thần "chỉ thiết lập khung giờ, hệ thống tự dời". Bill-strip 1.8rem + bar chart Trước/Sau
ngay đầu Tổng quan — đủ "đập vào mắt trong 5 giây" nếu đã có kết quả.

**Đối chiếu judge_review Tiêu chí 6:** nhãn Linh hoạt/Cố định **ĐÃ FIX**
(`ApplianceManager.jsx:292,296` khớp `OptimizeTab.jsx:144` + `GuideTab.jsx:51-58`); card ESG
**ĐÃ GỠ**; ghost lần đầu **CÒN ĐÚNG**; BillChart 18h **VÁ MỘT NỬA**; quantity trong chart +
override âm thầm **CHƯA FIX**; dead code **CÒN NGUYÊN +3 file**.

**Điểm ước lượng:** III.6 = **7/10** · I.4 = **11,5/15**.

---

## 6. Bảng ánh xạ Rubric

### Vòng chung kết (mục III — 100 điểm)

| Tiêu chí | Trọng số | Điểm hiện tại | Hành động để đạt tối đa |
|---|---|---|---|
| III.1 Tính năng & hoàn thiện (try/except, demo không crash, clean code) | 25 | **20–21** | Sửa 4 Critical (A1–A4 mục 7); thêm auth cho `/api/alert`; check pin-hour ở `/optimize`; xóa 7 file dead code (xóa nguyên file, không refactor) → tiệm cận 24 |
| III.2 Giải quyết vấn đề thực tiễn (QUBO ánh xạ đúng ràng buộc) | 20 | **14** | Vá λ_power < λ_onehot + guard 422 (hết crash biên); khai báo hạn chế "H_cost/H_solar theo giờ bắt đầu" vào README/docstring; sửa README bổ sung diagonal + F(h) của H_power; bỏ chữ "never" về λ → 17–18 |
| III.3 Chất lượng kỹ thuật (Qiskit, tuning hyperparameters) | 15 | **11** | Thêm cột "xác suất đo trúng optimum" vào bảng phân tích; đồng bộ `/qaoa-analysis` với run thật (coerce + threshold + TOU + warm-start); gọi đúng tên "greedy-seeded initial state" khi pitch → 13–14 |
| III.4 Trình bày & thuyết phục (pitching script) | 15 | **12** (tăng từ 8–9: `docs/pitching_script.md` đã tồn tại, chất lượng tốt, có sẵn câu chống phản biện) | Bổ sung vào script: câu trả lời Chủ nhật-TOU (E-M1) và "λ đủ lớn không?" (Q-H1); 1 trang tóm tắt tiếng Việt cho README → 13–14 |
| III.5 Kết quả triển khai thực tế (dữ liệu EVN thật) | 15 | **12,5–13** | Vá Chủ nhật TOU 26/30; dẫn nguồn PVGIS cho solar 525 kWh; chốt các `[CẦN XÁC MINH]` trong catalog → 14 |
| III.6 UX/UI | 10 | **7** | Gỡ debug overlay + .catch (U-C1); vá 5 biến CSS Landing; đậm Gantt cells + tăng cỡ chữ giờ; sửa GuideTab; stroke chart đậm hơn → 8,5–9 |
| **Tổng** | **100** | **≈ 76–77** | **Trần thực tế sau khi sửa: ≈ 86–89** |

### Vòng lên ý tưởng (mục I — 100 điểm)

| Tiêu chí | Trọng số | Điểm hiện tại | Hành động |
|---|---|---|---|
| I.1 Tính thực tiễn (pain lượng hóa, giá bậc thang) | 25 | **21** | Pain đã lượng hóa bằng VNĐ + biểu giá thật có nguồn; thêm chú thích baseline dưới "Hóa đơn trước" để chống nghi ngờ thổi phồng |
| I.2 Sáng tạo & độc đáo (Quantum/QAOA) | 20 | **18** | QAOA là lõi thật, không phải trang trí (có bảng hyperparameter trong UI); giữ vững câu trả lời Q1 trong pitching script |
| I.3 Khả thi kỹ thuật (PoC 4–6 qubit, mượt trên laptop) | 15 | **12** | Enforce trần ≤20 biến (Q-C2) — biến claim "chạy mượt" từ "đúng khi dữ liệu ngoan" thành "được bảo đảm" → 13–14 |
| I.4 Phù hợp Smart Life (tiện lợi) | 15 | **11,5** | Luồng 5-click + auto-optimize rất đúng đề; sửa GuideTab lệch nội dung + badge duration-override → 13 |
| I.5 Kết quả mong đợi (biểu đồ so sánh VNĐ) | 15 | **12** | Bill-strip + bar chart có; thêm ghost "trước" cho lần tối ưu đầu (U-H6) và thống nhất baseline BillChart → 13–14 |
| I.6 Chất lượng tài liệu (sơ đồ, Gantt) | 10 | **8** | README có mermaid + Gantt UI có thật; thêm 1 trang tiếng Việt tóm tắt → 9 |
| **Tổng** | **100** | **≈ 82–83** | |

### Vòng phụ (mục II — điểm cộng)

| Mức | Yêu cầu | Trạng thái | Ghi chú |
|---|---|---|---|
| Dễ +8 | Cảnh báo tổng công suất vượt ngưỡng (5000W) | ✅ Có thật | H_power trong QUBO + lưới cảnh báo 24h trên UI (`OptimizeTab.jsx:12-29`) + threshold theo role (`test_power_threshold.py`) |
| Trung bình +15 | ML forecast thời gian chạy → đưa vào QAOA | ✅ Có thật | `forecaster.py` + `duration_overrides` chảy vào QUBO — nhưng phải sửa B-C2 (inf) và thêm badge U-M3 trước khi khoe |
| Khó +25 | Hybrid quantum-classical + điện mặt trời trong hàm mục tiêu | ✅ Có thật | H_solar trong QUBO + warm-start greedy + brute-force đối chiếu = hybrid đúng nghĩa; solar là trục giá trị chính |

---

## 7. Danh sách hành động ưu tiên (Critical → Low)

> Effort là ước tính cho người quen codebase. Thứ tự trong nhóm = thứ tự nên làm.
> **Mọi thay đổi dưới đây cần được duyệt trước khi thực hiện (audit này read-only).**

### 🟥 Critical — demo có thể chết ngay trước giám khảo (~1,5–2h tổng)

| # | File | Mô tả | Đề xuất | Effort |
|---|---|---|---|---|
| A1 | `client/src/main.jsx:7-12` + `History.jsx:14`, `FeedbackTab.jsx:14`, `ProfileTab.jsx:23-26` | Debug overlay in hộp đỏ + `innerHTML +=` giết event listener React; 3 promise không catch | Xóa 2 handler debug (hoặc chỉ `console.error`); thêm `.catch(() => setError(...))` cho 3 chỗ | 10' |
| A2 | `backend/core/qubo_builder.py:116-117`, `quantum_runner.py:373`, `optimize_router.py:437` | Infeasible công suất → ValueError → 500 (đã tái hiện với 6000W/threshold 5000W) | `lambda_power = 5e5` (< lambda_onehot); guard trong `_build_result`: bitstring không one-hot → HTTPException 422 "…vượt ngưỡng công suất tại mọi giờ ứng viên" | 30' |
| A3 | `backend/api/optimize_router.py` (đầu `/optimize`), `quantum_runner.py:357` | Không trần qubit; brute-force 2ⁿ chạy vô điều kiện → treo worker | `if n_vars > 20: raise HTTPException(422)`; skip brute-force đối chiếu khi n > 20; dedupe + `max_length=6` cho `candidate_hours` | 30' |
| A4 | `backend/api/optimize_router.py:79, :504` | `duration_overrides: "inf"/"nan"` → vòng lặp vô hạn `_hourly_load:141` | Validator: `math.isfinite(v) and 0 < v <= 24` | 10' |

### 🟧 High (~1–1,5h tổng)

| # | File | Mô tả | Đề xuất | Effort |
|---|---|---|---|---|
| B1 | `backend/api/alert_router.py:16` | Endpoint gửi email không auth | Thêm `Depends(get_current_user)` | 5' |
| B2 | `backend/api/optimize_router.py:386` | Pin hour ngoài 0–23 → 500 (recompute có check, optimize không) | Copy check `0 <= hour <= 23` từ `:543` | 5' |
| B3 | `client/src/App.css` (block `.landing-page`) | 6 biến CSS không tồn tại → Landing vỡ màu, animation mất cột | Thêm `--error:#ef4444; --neon-cyan:#06b6d4; --neon-emerald:#10b981; --neon-purple:#8b5cf6; --quantum-glow:rgba(45,212,191,.5)` | 5' |
| B4 | `client/src/App.css:204,210,214,221` | Gantt cells 1,15:1, chữ giờ 0.62rem — vô hình trên máy chiếu | cell-valid đậm hơn, cell-on 75% alpha, ghost 2px, header giờ ≥0.75rem | 15' |
| B5 | `client/src/pages/GuideTab.jsx:46-47,51-52,71-75` | Guide mô tả sai tab Dự báo + form không còn tồn tại | Viết lại 3 đoạn text khớp UI thật | 10' |
| B6 | `client/src/AppData.jsx:298-299,331-333` | Lỗi mạng nuốt im lặng → lịch ≠ tiền | Revert localSchedule + hiện lỗi dưới Gantt | 20' |
| B7 | `client/src/api.js:147-158`, `AppData.jsx:382` | SSE: !ok im lặng; đứt stream mất text | `if (!response.ok) throw`; catch nối "[Kết nối gián đoạn]" | 10' |
| B8 | `README.md:163-165`, `qubo_builder.py:203-209` | Claim "never bought back" sai (chứng minh được) | Đổi thành "với dải input đã validate (power ≤ X, quantity ≤ Y)" — làm sau A2/A3 | 10' |
| B9 | `backend/db/alembic/` + `models.py:66` | `quantity` NOT NULL không server_default | **[HỎI TRƯỚC — đổi schema]** migration `server_default="1"`; xác minh DB production có cột | 20'+xác minh |

### 🟨 Medium (làm nếu còn thời gian)

| # | File | Mô tả | Đề xuất | Effort |
|---|---|---|---|---|
| C1 | `backend/api/optimize_router.py:161-168` | TOU business bỏ Chủ nhật → cao điểm thừa ~14% | Nhân cao điểm ×26/30, dồn 4/30 vào bình thường; ghi giả định | 20' |
| C2 | `client/src/components/BillChart.jsx:13,50` | Bỏ quantity + duration 1.0h cho thiết bị cố định → 2 tab 2 tổng | Nhân quantity; lấy duration từ usage_windows | 20' |
| C3 | `client/src/AppData.jsx:258-260` + `OptimizeTab.jsx` | Duration override áp âm thầm vĩnh viễn | Badge "Đang dùng thời lượng dự báo" + nút gỡ | 20' |
| C4 | `client/src/components/BillChart.jsx:69-85` + axis | Stroke 2,15–2,43:1 — mờ trên máy chiếu | `#B45309`/`#0E7490`, axis `#6b6b6b` | 5' |
| C5 | `backend/core/qubo_builder.py` + README | Khai báo hạn chế "H_cost/H_solar theo giờ bắt đầu"; bổ sung diagonal+F(h) vào README | Chỉ docs | 15' |
| C6 | `backend/core/quantum_runner.py:187-242` | Thêm cột "P(đo trúng optimum)" — bằng chứng tuning thật | Đếm tỉ lệ shots trúng bitstring optimum | 30' |
| C7 | `backend/api/optimize_router.py:588-595` | Đồng bộ `/qaoa-analysis` với run thật (coerce+threshold+TOU+warm-start) | Truyền cùng tham số như `:426-428` | 20' |
| C8 | `backend/api/feedback_router.py:74-80`, `weather_router.py:70` | GET /feedback lộ mọi user; /weather không auth | Thu hẹp scope + thêm Depends | 15' |
| C9 | `client/src/pages/OptimizeTab.jsx:117` | "Hóa đơn trước" không chú thích baseline | 1 dòng: "= chạy tải linh hoạt vào giờ bất lợi nhất trong khung cho phép" | 5' |

### 🟩 Low (đừng đụng đêm trước khi thi — trả lời miệng theo pitching script)

- Xóa 7 file dead code (`Dashboard.jsx`, `OptimizePanel.jsx`, `ResultsPanel.jsx`,
  `QuantumReactor.jsx`, `TiltCard.jsx`, `AnimatedBackground.jsx`, `useCountUp.js`) — xóa nguyên
  file, không refactor.
- `calc.py:26` sửa comment ngày hiệu lực 29/5 → 10/5 (QĐ 1279); TODO cho `VAT_RATE` hết hạn
  31/12/2026.
- Migrate `google.generativeai` → `google.genai`; index `user_id`; lat/lon bounds; thống nhất
  min-length mật khẩu 8; màu lỗi đỏ thay teal ở Feedback/Profile/Admin; định nghĩa `--error`/
  `--indigo` còn thiếu trong app chính; code-split bundle 1.1MB.
- Ghi nhận để **trả lời miệng** (đã có sẵn trong `pitching_script.md`/`judge_review.md` mục 3):
  H_power theo giờ bắt đầu, quantity gộp khối, không FIT/bán điện dư, giá biên household vs TOU
  business, quy ước làm tròn giờ lửng 17h/22h — bổ sung thêm 2 câu mới: **Chủ nhật-TOU** và
  **"λ=1e6 đủ lớn không?"**.

---

*Báo cáo bởi audit đa luồng (4 subagent chuyên trách + tổng hợp), 2026-07-03. Không file nào
ngoài chính báo cáo này được tạo/sửa. Mọi lỗi Critical về thuật toán đã được tái hiện bằng tính
toán read-only trước khi kết luận; biểu giá EVN xác minh online có nguồn dẫn ở mục 3.*
