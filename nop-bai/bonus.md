# Phụ Lục Bonus - Lab Day 21

Phụ lục cho [bao-cao.md](bao-cao.md). Số liệu lấy từ lần chạy trên **44.722 mẫu**
(`train_batch1` sau khi gộp `train_batch2`), tham số `n_estimators=200`,
`learning_rate=0.1`, `max_depth=5`, chấm trên `holdout.csv` (500 mẫu).

| Bonus | Trạng thái | Nơi cài đặt |
|---|---|---|
| 1. MLflow từ xa với DagsHub | Đã làm | `cicd.yml` job Train, `src/train.py` |
| 2. Điều chỉnh ngưỡng quyết định | Đã làm | `src/train.py` → `sweep_threshold()` |
| 3. Báo cáo precision / recall tự động | Đã làm | `src/train.py` → `write_detail_report()`, `cicd.yml` job Train |
| 4. Hoàn trả về phiên bản trước | Đã làm | `cicd.yml` job Train + Quality Gate + Release |
| 5. Cảnh báo lệch lạc dữ liệu | Đã làm | `src/train.py` → `check_class_balance()` |

---

## Bonus 1 - Tracking MLflow Từ Xa Với DagsHub

**Vấn đề của cách cũ:** khi pipeline chạy trên GitHub Actions, `mlflow` ghi vào thư mục cục bộ
của runner. Runner bị xóa ngay sau khi job kết thúc, nên mọi thí nghiệm do CI huấn luyện đều
biến mất — chỉ còn `report.json` trong artifact. Nghĩa là cuốn nhật ký thí nghiệm chỉ ghi được
các lần chạy trên máy cá nhân, đúng thứ mà MLflow sinh ra để tránh.

**Cách sửa:** trỏ MLflow về tracking server miễn phí của DagsHub gắn với chính repo này.

Bước `Configure remote MLflow tracking (DagsHub)` trong job Train nạp ba biến môi trường từ
GitHub Secrets vào `$GITHUB_ENV`:

| Secret | Giá trị |
|---|---|
| `MLFLOW_TRACKING_URI` | `https://dagshub.com/pbnjs4224/Track2_Day21_2A2022601506_PhamGiaBao.mlflow` |
| `MLFLOW_TRACKING_USERNAME` | `pbnjs4224` |
| `MLFLOW_TRACKING_PASSWORD` | access token của DagsHub |

`src/train.py` không cần đổi logic: `mlflow` tự đọc `MLFLOW_TRACKING_URI` từ biến môi trường,
nên cùng một file chạy được cả cục bộ lẫn từ xa. Script chỉ in thêm URI đang dùng
(`[MLFLOW] Tracking URI: ...`) để log của pipeline chứng minh nó ghi đi đâu.

Hai lựa chọn thiết kế có chủ ý:

1. **Bước cấu hình không bắt buộc.** Nếu `MLFLOW_TRACKING_URI` rỗng, bước này thoát sớm và
   MLflow ghi cục bộ như cũ. Ai clone repo mà không có tài khoản DagsHub vẫn chạy được
   pipeline.
2. **`log_model` được bọc `try/except`.** Ghi tham số và chỉ số là bắt buộc, lỗi thì dừng
   pipeline. Riêng việc upload artifact mô hình lên tracking server là phần *quan sát*, không
   phải sản phẩm giao đi — sản phẩm là `models/model.joblib` được publish lên S3 ở job Release.
   Một tracking server chập chờn không được phép làm hỏng cả lần huấn luyện.

Kết quả: mỗi lần GitHub Actions huấn luyện, run được ghi lên DagsHub kèm `n_estimators`,
`learning_rate`, `max_depth` và cả năm chỉ số (`f1_score`, `accuracy`, `positive_rate`,
`best_threshold`, `f1_at_best_threshold`) — xem được từ bất cứ đâu, không cần mở máy cá nhân.
Ảnh `06-dagshub-mlflow.png`.

---

## Bonus 2 - Điều Chỉnh Ngưỡng Quyết Định

`model.predict()` gán nhãn 1 khi xác suất vượt 0.5. Với dữ liệu 75/25 thì ngưỡng này
thiên vị lớp đa số. `sweep_threshold()` lấy `predict_proba(X_eval)[:, 1]` rồi quét ngưỡng
từ 0.10 đến 0.90, bước 0.05, tính `f1_score` tại từng ngưỡng.

| Ngưỡng | f1_score lớp dương |
|---|---|
| 0.50 (mặc định) | 0.7354 |
| **0.30 (tốt nhất)** | **0.7537** |

**Nhận xét:** hạ ngưỡng từ 0.50 xuống 0.30 làm F1 tăng **+0.0183**. Hạ ngưỡng nghĩa là
chấp nhận gán nhãn "thu nhập cao" ở mức tự tin thấp hơn, đổi một ít precision lấy nhiều
recall hơn — đúng hướng cần đi khi lớp dương là thiểu số và đang bị bỏ sót nhiều
(xem Bonus 3).

Hai giá trị `best_threshold` và `f1_at_best_threshold` được ghi vào `outputs/report.json`
và log lên MLflow cùng `f1_score`, `accuracy`, `positive_rate`.

**Lưu ý quan trọng:** quality gate vẫn dùng `f1_score` tại ngưỡng mặc định 0.5, **không**
dùng `f1_at_best_threshold`. Lý do: ngưỡng tốt nhất được dò trên chính tập holdout, nên
0.7537 là con số lạc quan (đã nhìn vào đáp án). Dùng nó làm căn cứ chặn triển khai sẽ làm
gate dễ dãi hơn thực tế. Muốn dùng ngưỡng đã tinh chỉnh cho sản phẩm thì phải dò trên một
tập validation riêng, tách khỏi tập chấm điểm.

---

## Bonus 3 - Báo Cáo Precision / Recall Tự Động

`write_detail_report()` ghi `outputs/detail.txt` sau mỗi lần huấn luyện; job Train trong
`cicd.yml` upload file này cùng `report.json` trong artifact tên `report`.

Confusion matrix trên holdout (hàng = thực tế, cột = dự đoán):

|  | dự đoán 0 | dự đoán 1 |
|---|---|---|
| **thực tế 0** | 359 | 17 |
| **thực tế 1** | 42 | 82 |

| Lớp | precision | recall | f1 | support |
|---|---|---|---|---|
| thu_nhap_thap (0) | 0.8953 | 0.9548 | 0.9241 | 376 |
| thu_nhap_cao (1) | 0.8283 | 0.6613 | 0.7354 | 124 |

**Sai lầm nào tốn kém hơn?** Với bài toán này, **bỏ sót người thu nhập cao (recall thấp)
tốn kém hơn**. Con số nói rõ điều đó: mô hình bỏ sót 42 trường hợp nhưng chỉ báo động nhầm
17 — recall lớp dương chỉ 0.6613 trong khi precision đạt 0.8283, tức là lỗi đang dồn hết về
phía bỏ sót. Đây chính là kiểu thất bại mà accuracy che giấu: 359 + 82 = 441/500 dự đoán
đúng cho accuracy 0.882 trông rất đẹp, trong khi hơn một phần ba lớp cần phát hiện bị lọt
lưới. Nếu đầu ra được dùng để chọn đối tượng tiếp cận, một false positive chỉ tốn thêm một
lần liên hệ, còn một false negative là mất hẳn cơ hội. Đó cũng là lý do Bonus 2 hạ ngưỡng
xuống 0.30 lại cải thiện được F1.

---

## Bonus 4 - Hoàn Trả Về Phiên Bản Trước

Cơ chế an toàn hai lớp, đồng thời sửa một lỗ hổng của pipeline gốc.

**Lỗ hổng ở phiên bản trước:** job Train đẩy `model.joblib` lên
`s3://<bucket>/artifacts/current/` **trước** khi quality gate chạy. Nghĩa là một mô hình yếu
vẫn ghi đè mô hình đang phục vụ — điều này đã thực sự xảy ra ở
[run #2](https://github.com/Brianphams2/Track2_Day21_2A2022601506_PhamGiaBao/actions/runs/32494775032).
Gate chỉ chặn được lệnh `systemctl restart`; nếu VM tự khởi động lại vì bất kỳ lý do gì,
nó sẽ nạp đúng mô hình yếu đó.

**Cách sửa:** mô hình không còn được publish ở job Train nữa. Nó được giữ dưới dạng artifact
của GitHub Actions, và chỉ được `aws s3 cp` lên S3 ở job **Release** — tức là sau khi gate đã
qua. `artifacts/current/model.joblib` từ nay chỉ chứa mô hình đã vượt chốt.

**Luồng so sánh:**

1. Job Train, **trước khi huấn luyện**, tải `artifacts/current/report.json` (report của mô hình
   đang chạy) và xuất ra `prev_f1`. Nếu file chưa tồn tại thì bỏ qua, không làm hỏng pipeline.
2. Job Quality Gate kiểm tra hai chốt:
   - Chốt tuyệt đối: `f1_score >= 0.65`.
   - Chốt tương đối: `f1_score` mới `>=` `f1_score` của mô hình đang chạy.
3. Job Release publish cả `model.joblib` lẫn `report.json` lên S3, nên `report.json` vừa là
   bằng chứng vừa là mốc so sánh cho lần chạy kế tiếp.

Ở lần chạy đầu tiên sau khi đổi pipeline
([run #5](https://github.com/Brianphams2/Track2_Day21_2A2022601506_PhamGiaBao/actions/runs/32501465376)),
S3 chưa có `report.json` nên chốt rollback tự bỏ qua và log in
`Chua co model tham chieu tren S3 - bo qua chot rollback` — đúng thiết kế, để lần chạy đầu
không bị chặn oan. Job Release của chính run đó đã publish `report.json` lên S3, nên từ lần
chạy kế tiếp trở đi log của Quality Gate mới in dòng so sánh thật, dạng:
`So sanh voi model dang chay: moi 0.7354 vs cu 0.7354 (chenh lech +0.0000)`.

---

## Bonus 5 - Cảnh Báo Lệch Lạc Dữ Liệu

`check_class_balance()` chạy **trước** `model.fit()`, tính tỷ lệ lớp dương của tập huấn luyện
và so với tỷ lệ tham chiếu 24,8% của bộ Adult gốc. Lệch quá 5 điểm phần trăm thì in cảnh báo
`[DRIFT] CANH BAO ...` vào log pipeline.

Kết quả lần chạy trên 44.722 mẫu:

```
[DRIFT] OK: ty le lop duong = 0.2478, lech 0.02 diem phan tram so voi tham chieu 0.2480.
```

Tỷ lệ 0.2478 lệch 0,02 điểm phần trăm — đúng như kỳ vọng, vì `train_batch2` được chia ngẫu
nhiên từ cùng nguồn với `train_batch1` nên cùng phân phối. Giá trị này được ghi vào
`outputs/report.json` dưới khóa `positive_rate` và log lên MLflow, để sau này so sánh giữa các
lần chạy chứ không chỉ đọc một lần rồi bỏ.

---

