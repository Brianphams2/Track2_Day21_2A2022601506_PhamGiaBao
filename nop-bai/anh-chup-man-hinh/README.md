# Chuỗi Ảnh Chụp Màn Hình Theo Thứ Tự

Đặt ảnh vào chính thư mục này, **đúng tên file** dưới đây. Bài chấm theo đúng thứ tự
01 → 05, nên tên file sai hoặc thiếu ảnh sẽ bị tính là thiếu bằng chứng cho hạng mục
tương ứng.

---

## `01-mlflow-ui.png` - MLflow UI (Bước 1)

Chụp ở màn hình danh sách các lần chạy của MLflow UI (`http://localhost:5000`), sau khi đã
sắp xếp theo `f1_score` giảm dần.

Ảnh phải thấy rõ:

- Ít nhất **3 lần chạy** với siêu tham số khác nhau.
- Cột `f1_score` **và** cột `accuracy` của từng lần chạy.
- Các cột siêu tham số `n_estimators`, `learning_rate`, `max_depth`.

Cách hiện thêm cột trong MLflow UI: nhấn nút **Columns** ở góc phải bảng và tick các
metric/param cần hiển thị.

Chụp ở bước: [Bước 1, mục 1.8](../../tasks/buoc-1.md).

---

## `02-actions-buoc-2.png` - GitHub Actions ở Bước 2

Chụp trang chi tiết của một lần chạy workflow trong tab **Actions**.

Ảnh phải thấy rõ:

- Cả **bốn jobs**: Unit Test, Train, Quality Gate, Release — tất cả đều màu xanh.
- Tên/commit message của lần chạy, để xác nhận đây là lần chạy của Bước 2.

Chụp ở bước: [Bước 2, phần Kết Quả Cần Đạt](../../tasks/buoc-2.md).

Run đã hoàn thành: <https://github.com/Brianphams2/Track2_Day21_2A2022601506_PhamGiaBao/actions/runs/32493902550>

---

## `03-actions-buoc-3.png` - GitHub Actions ở Bước 3

Chụp lần chạy workflow được kích hoạt bởi **commit dữ liệu mới** (không phải commit code).

Ảnh phải thấy rõ:

- Commit message của lần chạy đúng là commit cập nhật dữ liệu ở Bước 3.
- Cả bốn jobs đều hoàn thành thành công.

Đây là bằng chứng cho hạng mục "một commit dữ liệu mới kích hoạt toàn bộ pipeline không
cần tác động thủ công", nên khác biệt so với ảnh `02` nằm ở commit message.

Chụp ở bước: [Bước 3, phần Kết Quả Cần Đạt](../../tasks/buoc-3.md).

Run commit dữ liệu đã hoàn thành: <https://github.com/Brianphams2/Track2_Day21_2A2022601506_PhamGiaBao/actions/runs/32495193074>

---

## `04-curl-api.png` - Kết quả gọi API trên VM

Chụp cửa sổ terminal chứa **cả hai lệnh và cả hai kết quả**:

```powershell
curl.exe http://3.89.87.129:8080/healthz
curl.exe -X POST http://3.89.87.129:8080/score -H "Content-Type: application/json" -d '{"features":[39,5,13,4,0,1,1,2174,0,40]}'
```

Ảnh phải thấy rõ:

- `/healthz` trả về `{"status": "ok"}`.
- `/score` trả về nhãn dự đoán hợp lệ (`thu_nhap_cao` hoặc `thu_nhap_thap`).
- Địa chỉ IP của VM trong lệnh (chứng minh gọi tới VM, không phải `localhost`).

Nếu hai lệnh chạy ở hai thời điểm khác nhau, được phép nộp thành hai file
`04a-curl-healthz.png` và `04b-curl-score.png`.

---

## `05-cloud-storage.png` - Cloud Storage Console

Chụp giao diện web của cloud storage (GCS / S3 / Azure Blob).

Ảnh phải thấy rõ:

- Thư mục `dvc/` chứa dữ liệu do DVC đẩy lên.
- File model tại `artifacts/current/model.joblib`.
- Tên bucket/container.

Nếu hai đường dẫn nằm ở hai màn hình khác nhau, được phép nộp thành hai file
`05a-storage-dvc.png` và `05b-storage-model.png`.

- DVC: <https://s3.console.aws.amazon.com/s3/buckets/amz01day21msv01506?region=us-east-1&prefix=dvc/&showversions=false>
- Model: <https://s3.console.aws.amazon.com/s3/buckets/amz01day21msv01506?region=us-east-1&prefix=artifacts/current/&showversions=false>

---

## Ảnh Tùy Chọn (cho phần Bonus)

Nếu bạn làm các thách thức nâng cao, thêm ảnh với tiền tố `06-` trở đi và mô tả ngắn
trong `bao-cao.md`. Ví dụ:

- `06-dagshub-mlflow.png` — Bonus 1: MLflow trên DagsHub.
- `07-quality-gate-chan.png` — quality gate chặn Release khi `f1_score < 0.65`.

Run quality gate đã chặn model yếu: <https://github.com/Brianphams2/Track2_Day21_2A2022601506_PhamGiaBao/actions/runs/32494775032>
