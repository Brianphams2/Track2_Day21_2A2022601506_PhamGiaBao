# Báo Cáo Lab Day 21 - CI/CD cho AI Systems

| | |
|---|---|
| Họ và tên | Phạm Gia Bảo |
| MSSV | 2A2022601506 |
| Lớp / Khóa | K4 |
| Repo GitHub | https://github.com/Brianphams2/Track2_Day21_2A2022601506_PhamGiaBao |
| Ngày nộp | 21/08/2026 |

---

## 1. Bộ Siêu Tham Số Đã Chọn và Lý Do

| Lần chạy | n_estimators | learning_rate | max_depth | f1_score | accuracy |
|---|---|---|---|---|---|
| 1 | 100 | 0.1 | 3 | 0.7109 | 0.8780 |
| 2 | 50 | 0.05 | 2 | 0.6051 | 0.8460 |
| 3 | 200 | 0.1 | 5 | 0.7149 | 0.8740 |

**Bộ siêu tham số đã chọn:** `n_estimators=200`, `learning_rate=0.1`, `max_depth=5`.

**Lý do:** Lần chạy 3 có F1 cao nhất (0.7149), vượt ngưỡng 0.65. Lần chạy 1 có accuracy cao nhất (0.8780) nhưng F1 thấp hơn, cho thấy chọn theo accuracy sẽ không tối ưu khả năng nhận diện lớp thu nhập cao. Cấu hình yếu với ít cây, learning rate thấp và cây nông chỉ đạt F1 0.6051; tăng số cây và độ sâu giúp boosting sửa được nhiều lỗi hơn.

---

## 2. Vì Sao Ngưỡng Chất Lượng Đặt Trên F1 Chứ Không Phải Accuracy

Dữ liệu chỉ có khoảng 24,8% mẫu thuộc lớp thu nhập trên 50K nên accuracy bị chi phối bởi lớp thu nhập thấp. Một mô hình luôn dự đoán lớp thấp vẫn đạt accuracy khoảng 0.752 nhưng F1 của lớp dương bằng 0 vì không phát hiện được người thu nhập cao nào. F1 cân bằng precision và recall của chính lớp dương, vì vậy phản ánh trực tiếp khả năng vừa hạn chế dự đoán nhầm vừa giảm bỏ sót lớp cần phát hiện. Gate dùng `f1_score(y_eval, preds)` với mặc định `pos_label=1`; không dùng weighted hay macro vì các cách tổng hợp đó có thể che khuất hiệu quả thật trên lớp thiểu số. Do đó ngưỡng F1 0.65 bảo vệ sản phẩm tốt hơn một ngưỡng accuracy tưởng như cao.

---

## 3. Khó Khăn Gặp Phải và Cách Giải Quyết

| Khó khăn | Nguyên nhân | Cách giải quyết |
|---|---|---|
| Hướng dẫn mặc định dùng GCP | Bài triển khai trên AWS | Ánh xạ GCS/GCE sang S3/EC2, dùng boto3 và IAM role |
| DVC push bị AccessDenied | Terminal dùng nhầm IAM user `Brianpham` | Chọn profile giới hạn `day21msv01506`, không lưu key trong repo |
| Release không SSH được vào EC2 | Secret chứa sai định dạng private key | Thay bằng deploy key hợp lệ, chạy lại Release và kiểm tra health |

---

## 4. So Sánh Bước 2 và Bước 3 (bắt buộc, 2 - 3 câu)

| | f1_score | accuracy |
|---|---|---|
| Bước 2 (chỉ `train_batch1`) | 0.7149 | 0.8740 |
| Bước 3 (thêm `train_batch2`) | 0.7354 | 0.8820 |

**Nhận xét:** Khi tăng dữ liệu huấn luyện từ 22.361 lên 44.722 mẫu, F1 tăng 0.0205 và accuracy tăng 0.0080 trên cùng tập holdout. Batch mới cùng phân phối nhưng bổ sung nhiều ví dụ lớp dương và các trường hợp biên, giúp mô hình tổng quát hóa tốt hơn; kết quả này không có nghĩa thêm dữ liệu luôn bảo đảm tăng điểm.
