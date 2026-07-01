# **\[AI GUIDELINES & RUBRIC\] Tiêu Chí Đánh Giá Cuộc Thi Smart Life**

**Dự án:** Q-SmartEnergy (Tối ưu hóa lập lịch thiết bị điện thông minh bằng thuật toán lượng tử QAOA)  
**Mục đích tài liệu:** Làm bối cảnh (Context) cho AI trong suốt quá trình phát triển dự án. AI BẮT BUỘC phải đối chiếu mọi giải pháp kỹ thuật, tài liệu, và mã nguồn với khung điểm dưới đây để tối ưu hóa khả năng giành giải.

## **I. CHIẾN LƯỢC TỐI ƯU ĐIỂM SỐ \- VÒNG LÊN Ý TƯỞNG (100 ĐIỂM)**

Mỗi bước đề xuất từ AI phải giải quyết trực tiếp các tiêu chí sau đây:

| Tiêu chí & Trọng số | Yêu cầu từ Ban Giám Khảo | Chỉ thị hành động cho AI (AI Actionable Directives) |
| :---- | :---- | :---- |
| **1\. Tính thực tiễn của vấn đề (25đ)** | Bài toán có tồn tại trong đời sống? Pain points có kiểm chứng, lượng hóa được không? | AI phải sử dụng các dataset giả lập hoặc thực tế về giá điện bậc thang / biểu giá theo giờ. Cần định lượng rõ ràng "Nỗi đau" (VD: Hóa đơn điện tăng 30% nếu sạc xe điện giờ cao điểm). |
| **2\. Tính sáng tạo & độc đáo (20đ)** | Ý tưởng mới mẻ, khác biệt? Cách tiếp cận sáng tạo? | Nhấn mạnh cốt lõi công nghệ **Quantum Computing (Thuật toán QAOA)** thay vì dùng AI/ML cổ điển. Đây là yếu tố định đoạt tính "độc đáo" cao nhất. |
| **3\. Tính khả thi kỹ thuật (15đ)** | Khả năng triển khai trong thời gian thi? Công nghệ phù hợp trình độ? | AI cần thiết kế một hệ thống Proof-of-Concept (PoC) thu gọn, sử dụng 4-5 qubits trên Qiskit Simulator. Đảm bảo code chạy mượt mà trên laptop thông thường mà không vướng giới hạn phần cứng. |
| **4\. Phù hợp chủ đề Smart Life (15đ)** | Ứng dụng công nghệ để tối ưu trải nghiệm sống, đúng tinh thần chủ đề. | Mô hình QUBO phải tập trung vào "Sự tiện lợi": Người dùng chỉ cần thiết lập khung giờ, hệ thống tự động dời lịch máy giặt/sạc xe mà không làm giảm tiện nghi sống. |
| **5\. Kết quả mong đợi (15đ)** | Hướng tới đối tượng nào? Thu về bao nhiêu? | Đối tượng là hộ gia đình có thiết bị điện tử tải cao. AI phải xuất ra biểu đồ so sánh rõ ràng: (Chi phí khi không có Q-SmartEnergy) vs (Chi phí khi dùng Q-SmartEnergy), đo lường bằng VNĐ. |
| **6\. Chất lượng trình bày tài liệu (10đ)** | Mô tả rõ ràng, có sơ đồ/mockup/user flow dễ hiểu. | AI hỗ trợ viết mã Python để sinh ra các biểu đồ Gantt (Gantt Chart) trực quan hóa lịch trình thiết bị, thay vì chỉ in ra các dòng text khô khan. |

## **II. CHIẾN LƯỢC VÒNG PHỤ (CỘNG ĐIỂM VÀO CHUNG KẾT)**

AI cần chuẩn bị các phương án leo thang kiến trúc tùy theo tiến độ của đội:

* **Mức Dễ (+8đ):** Thêm cảnh báo tự động khi tổng công suất của các thiết bị bật cùng lúc vượt ngưỡng an toàn của gia đình (VD: quá 5000W).  
* **Mức Trung bình (+15đ):** Viết một module nhỏ dự báo (Forecasting) bằng ML cổ điển để đoán thời gian hoàn thành công việc của máy giặt, sau đó đưa vào QAOA.  
* **Mức Khó (+25đ):** Áp dụng kiến trúc **Hybrid Quantum-Classical** mạnh mẽ hơn, hoặc đưa thêm yếu tố năng lượng tái tạo (điện mặt trời mái nhà) vào hàm mục tiêu (Cost Function).

## **III. BỘ TIÊU CHÍ VÒNG CHUNG KẾT (100 ĐIỂM)**

| Tiêu chí | Hướng dẫn triển khai cho AI |
| :---- | :---- |
| **1\. Tính năng & mức độ hoàn thiện (25đ)** | Code Python phải dọn dẹp sạch sẽ (clean code, OOP). Có xử lý ngoại lệ (Try/Catch) để Demo không bao giờ bị crash. |
| **2\. Giải quyết vấn đề thực tiễn (20đ)** | Mọi phương trình Toán học (QUBO) phải ánh xạ chính xác đến các ràng buộc ngoài đời thực. |
| **3\. Chất lượng kỹ thuật (15đ)** | Sử dụng thành thạo Qiskit-Optimization. Hiểu rõ cách tuning các tham số (Hyperparameters) của thuật toán lượng tử để đạt độ chính xác cao. |
| **4\. Trình bày & thuyết phục (15đ)** | AI phải hỗ trợ sinh kịch bản thuyết trình (Pitching Script) biến kiến thức Lượng tử hàn lâm thành câu chuyện tiết kiệm điện dễ hiểu nhất cho Giám khảo. |
| **5\. Kết quả triển khai thực tế (15đ)** | Sử dụng Data Generator sinh dữ liệu biểu giá điện thật của EVN để tăng sức thuyết phục. |
| **6\. Giao diện & trải nghiệm UX/UI (10đ)** | Tích hợp kết quả của Qiskit vào Streamlit hoặc Gradio để làm một Web App Demo đẹp mắt. |

## **IV. LUẬT LỆ KHẮT KHE (SYSTEM PROMPT) DÀNH CHO AI**

1. Trước khi viết code hay phương trình QUBO, AI BẮT BUỘC phải tự đánh giá: "Đoạn giải pháp này sẽ lấy được điểm ở tiêu chí nào trong Rubric?".  
2. KHÔNG đưa ra các giải pháp lan man, xa rời chủ đề Smart Life.  
3. Luôn đặt góc nhìn thực tiễn: Công nghệ phải đi đôi với tính ứng dụng. Giải pháp lượng tử dù hay đến đâu nhưng nếu thời gian chạy (execution time) quá lâu sẽ bị trừ điểm khả thi.