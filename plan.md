# Kế hoạch K4 CI/CD cho AI Systems - AWS `us-east-1`

> Repo: `https://github.com/Brianphams2/Track2_Day21_2A2022601506_PhamGiaBao`
>
> Kiến trúc: Windows PowerShell -> GitHub Actions -> Amazon S3 + EC2 Amazon Linux 2023.
>
> Region cố định cho toàn bộ lab: **`us-east-1`**.
>
> Tên S3 bucket do người dùng chọn: **`amz01day21msv01506`**.

## A. Những việc bạn cần làm trước

### A1. Xác nhận đúng tài khoản AWS và quyền

AWS CLI trên máy đã cài (`aws-cli/2.36.23`), đã đăng nhập và region mặc định đã là `us-east-1`. Bạn chỉ cần chạy lại để xác nhận đây là tài khoản muốn dùng:

```powershell
aws sts get-caller-identity
aws configure get region
```

Kết quả thứ hai phải là `us-east-1`. IAM user hiện tại cần quyền tạo/quản lý các tài nguyên lab sau:

- S3 bucket và object.
- IAM user/policy cho GitHub Actions.
- IAM role + instance profile cho EC2 đọc model từ S3.
- EC2 instance, key pair, security group và ingress rule.

Nếu tài khoản do trường/công ty quản lý, nhờ admin cấp các quyền trên. Không dùng root access key.

### A2. Kiểm tra billing trước khi tạo EC2

Trong AWS Console:

1. Mở **Billing and Cost Management**.
2. Kiểm tra phương thức thanh toán/tín dụng còn dùng được.
3. Nên tạo AWS Budget hoặc billing alert nhỏ.
4. Sau khi nộp bài sẽ **stop EC2**, chưa xóa S3 trước khi được chấm.

### A3. Xác nhận quyền quản trị repo GitHub

Bạn cần truy cập được:

- Repo -> **Settings -> Secrets and variables -> Actions** để tạo secrets.
- Repo -> **Settings -> General** để xác nhận repo ở chế độ Public.
- Tab **Actions** để xem và chụp workflow.

### A4. Thông tin không được gửi/commit

Không gửi vào chat, không commit và không để trong ảnh:

- AWS Secret Access Key.
- File private deploy key `income-api-deploy-v5`.
- Nội dung GitHub Secrets.

Các bước còn lại có command đầy đủ ở dưới. Những thao tác cần bạn trực tiếp làm trên giao diện là: xác nhận billing, nhập GitHub Secrets, chụp ảnh, và kiểm tra repo Public.

---

## 0. Trạng thái workspace

- Nhánh Git hiện tại: `main`; remote `origin` đã đúng.
- Python có sẵn 3.11, 3.12 và 3.14; dùng **Python 3.11** cho lab.
- AWS CLI đã hoạt động và cấu hình `us-east-1`.
- Chưa có `data/`, `.dvc/`; các file train, serve, test và workflow vẫn còn TODO.
- `plan.md` này chỉ là kế hoạch; chưa tạo tài nguyên tính phí.

Mở PowerShell tại repo:

```powershell
Set-Location 'C:\Users\baoph\Documents\Track2-20K\Track2_Day21_2A2022601506_PhamGiaBao'
$AWS_REGION='us-east-1'
$AWS_ACCOUNT_ID=aws sts get-caller-identity --query Account --output text
$BUCKET_NAME='amz01day21msv01506'
$BUCKET_NAME
```

Tên bucket S3 phải duy nhất toàn cầu. Trước khi tạo, xác nhận `amz01day21msv01506` chưa thuộc tài khoản khác; nếu bucket đã có trong chính tài khoản thì dùng lại sau khi xác nhận đó đúng bucket lab.

---

## 1. Chuẩn bị Python và dependency AWS

### 1.1 Sửa `requirements.txt`

Thay dependency GCP:

```text
dvc[gs]==3.50.1
google-cloud-storage==2.16.0
```

bằng:

```text
dvc[s3]==3.50.1
boto3
```

Giữ nguyên các dependency còn lại.

### 1.2 Tạo môi trường ảo

```powershell
py -3.11 -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python --version
dvc --version
pytest --version
```

Checkpoint: Python là 3.11.x, DVC và pytest gọi được.

---

## 2. Hoàn thiện code local

### 2.1 `src/train.py`

Điền tất cả TODO:

1. Đọc train và holdout bằng pandas.
2. Tách cột `target`.
3. Log ba hyperparameter vào MLflow.
4. Tạo `GradientBoostingClassifier(**params, random_state=42)`.
5. Tính `f1_score(y_eval, preds)` cho lớp dương và `accuracy_score`.
6. Log cả `f1_score`, `accuracy`, model.
7. Lưu `outputs/report.json` và `models/model.joblib`.
8. Trả `float(f1)`.

Không dùng `average="weighted"` hoặc `average="macro"`.

### 2.2 `tests/test_train.py`

- Tạo 200 mẫu giả, 10 feature, nhãn 0/1 với seed 0.
- 160 dòng train, 40 dòng holdout.
- Ba test: giá trị trả về là float `[0,1]`; report có đủ hai metric; model được tạo.

### 2.3 Chuyển `src/serve.py` sang S3

Thay `google.cloud.storage` bằng `boto3`:

- `s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION", "us-east-1"))`.
- Khi start, gọi `s3.download_file(ARTIFACT_BUCKET, "artifacts/current/model.joblib", MODEL_PATH)`.
- EC2 dùng IAM role, không lưu AWS access key trên VM.
- `GET /healthz` trả `{"status": "ok"}`.
- `POST /score` kiểm tra đúng 10 feature, trả `prediction` kiểu int và label hợp lệ.

### 2.4 Chuyển `.github/workflows/cicd.yml` sang AWS

Workflow giữ đúng bốn job nối tiếp:

```text
Unit Test -> Train -> Quality Gate -> Release
```

Các phần cần điền:

- Unit Test: `pytest tests/ -v`.
- Job Train thêm `aws-actions/configure-aws-credentials@v4` với:
  - `aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}`
  - `aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}`
  - `aws-region: us-east-1`
- DVC: `dvc pull data/train_batch1.csv.dvc data/holdout.csv.dvc`.
- Train: `python src/train.py`.
- Đọc F1 từ report và ghi vào `$GITHUB_OUTPUT`.
- Upload: `aws s3 cp models/model.joblib s3://${{ secrets.ARTIFACT_BUCKET }}/artifacts/current/model.joblib`.
- Gate: ép output thành `float`, chặn nếu F1 `< 0.65`.
- Release: SSH vào EC2, `sudo systemctl restart income-api`, đợi và curl `/healthz`.

Trigger phải gồm:

```yaml
paths:
  - 'data/**.dvc'
  - 'src/**.py'
  - 'params.yaml'
```

### 2.5 Unit test local

```powershell
pytest tests/ -v
```

Checkpoint: `3 passed`.

---

## 3. Tạo dữ liệu và ba thí nghiệm MLflow

```powershell
python prepare_data.py
(Import-Csv data\train_batch1.csv).Count
(Import-Csv data\holdout.csv).Count
(Import-Csv data\train_batch2.csv).Count
```

Kết quả: `22361`, `500`, `22361`.

Thiết lập MLflow trong PowerShell:

```powershell
$env:MLFLOW_TRACKING_URI='sqlite:///mlflow.db'
$env:MLFLOW_ARTIFACT_ROOT='./mlartifacts'
```

Chạy lần lượt ba cấu hình sau, sửa `params.yaml` trước mỗi lần rồi chạy `python src/train.py`:

| Lần | n_estimators | learning_rate | max_depth |
|---|---:|---:|---:|
| 1 | 100 | 0.1 | 3 |
| 2 | 50 | 0.05 | 2 |
| 3 | 200 | 0.1 | 5 |

Sau mỗi lần:

```powershell
python src/train.py
Get-Content outputs\report.json
```

Ghi F1/accuracy thật vào `nop-bai/bao-cao.md`. Cuối cùng để bộ có F1 cao nhất và F1 >= 0.65 trong `params.yaml`.

Mở MLflow:

```powershell
python -m mlflow ui --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5000
```

Tại `http://localhost:5000`, bật cột F1, accuracy và ba params; sắp xếp F1 giảm dần; chụp bằng `Win + Shift + S` thành:

`nop-bai/anh-chup-man-hinh/01-mlflow-ui.png`

---

## 4. Tạo S3 và DVC remote

### 4.1 Tạo bucket đúng `us-east-1`

Không truyền `LocationConstraint` cho `us-east-1`:

```powershell
aws s3api create-bucket --bucket $BUCKET_NAME --region us-east-1
aws s3api put-public-access-block --bucket $BUCKET_NAME --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-encryption --bucket $BUCKET_NAME --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api get-bucket-location --bucket $BUCKET_NAME
```

Với `us-east-1`, `get-bucket-location` có thể trả `null`/`None`; đó là bình thường.

### 4.2 Cấu hình DVC và đẩy dữ liệu

```powershell
dvc init
dvc remote add -d labstore "s3://$BUCKET_NAME/dvc"
dvc add data/train_batch1.csv
dvc add data/holdout.csv
dvc add data/train_batch2.csv
dvc push
aws s3 ls "s3://$BUCKET_NAME/dvc/" --recursive
```

DVC dùng AWS credentials local hiện có; không ghi access key vào `.dvc/config`.

Checkpoint:

```powershell
git check-ignore -v data\train_batch1.csv
git status --short
```

Git chỉ theo dõi ba file `.csv.dvc`, không theo dõi CSV thật.

---

## 5. Tạo IAM identity cho CI và role cho EC2

### 5.1 GitHub Actions IAM user

IAM user riêng đã chọn là `day21msv01506`, không dùng access key của IAM user cá nhân. Inline policy `S3D21` chỉ cấp quyền cho bucket lab với các quyền:

- Bucket: `s3:ListBucket`, `s3:GetBucketLocation` trên `arn:aws:s3:::<BUCKET_NAME>`.
- Object: `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:AbortMultipartUpload` trên:
  - `arn:aws:s3:::<BUCKET_NAME>/dvc/*`
  - `arn:aws:s3:::<BUCKET_NAME>/artifacts/*`

Có thể làm tại AWS Console -> **IAM -> Users -> Create user -> Permissions -> Create inline policy**. Sau đó tạo đúng một access key cho **Application running outside AWS**.

Để DVC local dùng đúng IAM user này mà không sửa credentials mặc định, cấu hình profile riêng (tự nhập key tại prompt, không gửi key qua chat):

```powershell
aws configure --profile day21msv01506
# AWS Access Key ID: nhập key của user day21msv01506
# AWS Secret Access Key: nhập secret của user day21msv01506
# Default region name: us-east-1
# Default output format: json
$env:AWS_PROFILE='day21msv01506'
aws sts get-caller-identity
aws s3api head-bucket --bucket amz01day21msv01506 --region us-east-1
```

Identity phải là `user/day21msv01506` và `head-bucket` không báo lỗi. Mỗi terminal PowerShell mới cần đặt lại `$env:AWS_PROFILE='day21msv01506'` trước lệnh DVC/AWS của lab.

Đây là bước bạn nên trực tiếp làm vì secret chỉ hiển thị đầy đủ một lần. Giữ màn hình/file tạm an toàn để nhập GitHub Secrets ở mục 8 rồi xóa/rotate sau khi chấm.

### 5.2 EC2 instance role

Tạo role `income-api-ec2-role` với trusted entity **AWS service -> EC2**. Gắn inline policy chỉ cho phép:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::<BUCKET_NAME>/artifacts/current/model.joblib"
  }]
}
```

Khi tạo role cho EC2 trong IAM Console, AWS đồng thời tạo instance profile cùng tên `income-api-ec2-role`. Khi launch EC2 chọn profile/role này. Dùng role giúp VM tải model mà không cần copy AWS access key lên máy.

---

## 6. Tạo EC2 tại `us-east-1`

### 6.1 Key pair và security group

```powershell
$VPC_ID=aws ec2 describe-vpcs --region us-east-1 --filters Name=is-default,Values=true --query 'Vpcs[0].VpcId' --output text
$SUBNET_ID=aws ec2 describe-subnets --region us-east-1 --filters "Name=vpc-id,Values=$VPC_ID" Name=default-for-az,Values=true --query 'Subnets[0].SubnetId' --output text
$SG_ID=aws ec2 create-security-group --region us-east-1 --group-name income-api-sg --description 'Income API lab' --vpc-id $VPC_ID --query GroupId --output text
aws ec2 authorize-security-group-ingress --region us-east-1 --group-id $SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --region us-east-1 --group-id $SG_ID --protocol tcp --port 8080 --cidr 0.0.0.0/0
```

GitHub-hosted runner cần SSH vào EC2 từ IP động, nên lab tạm mở port 22 và 8080 công khai. SSH vẫn bắt buộc private key. Sau khi chấm xong, xóa security group hoặc đóng port 22; không cài mật khẩu SSH trên VM.

Tạo key pair và lưu ngoài Git:

```powershell
$KEY_PATH=Join-Path $env:USERPROFILE '.ssh\income-api-deploy-v5'
# Deploy key hiện tại đã được tạo local và public key đã được cài vào EC2.
# Không dùng lại khóa income-api-key.pem đã bị lộ và đã bị vô hiệu hóa trên EC2.
icacls $KEY_PATH /inheritance:r
icacls $KEY_PATH /grant:r "$env:USERNAME`:(R)"
```

### 6.2 Launch Amazon Linux 2023

Trong EC2 Launch Instance, chọn Quick Start **Amazon Linux**, AMI **Amazon Linux 2023 AMI**, architecture **64-bit (x86)** rồi launch `t3.micro`. Nếu dùng CLI, lấy AMI chính chủ AWS từ public SSM parameter:

```powershell
$AMI_ID=aws ssm get-parameter --region us-east-1 --name '/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64' --query 'Parameter.Value' --output text
$INSTANCE_ID=aws ec2 run-instances --region us-east-1 --image-id $AMI_ID --instance-type t3.micro --key-name income-api-key --security-group-ids $SG_ID --subnet-id $SUBNET_ID --iam-instance-profile Name=income-api-ec2-role --associate-public-ip-address --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=income-api}]' --query 'Instances[0].InstanceId' --output text
aws ec2 wait instance-status-ok --region us-east-1 --instance-ids $INSTANCE_ID
$VM_IP=aws ec2 describe-instances --region us-east-1 --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].PublicIpAddress' --output text
$VM_IP
```

### 6.3 Cài service trên EC2

```powershell
ssh -i $KEY_PATH "ec2-user@$VM_IP"
```

Trên EC2 (Bash):

```bash
sudo dnf update -y
sudo dnf install -y python3 python3-pip
python3 -m venv ~/income-api-venv
~/income-api-venv/bin/pip install --upgrade pip
~/income-api-venv/bin/pip install fastapi uvicorn scikit-learn==1.4.2 joblib boto3
mkdir -p ~/models ~/src
exit
```

Copy API:

```powershell
scp -i $KEY_PATH src/serve.py "ec2-user@${VM_IP}:~/src/serve.py"
ssh -i $KEY_PATH "ec2-user@$VM_IP"
```

Trên EC2, thay `<BUCKET_NAME>`:

```bash
sudo tee /etc/systemd/system/income-api.service >/dev/null <<'EOF'
[Unit]
Description=Income Model Inference Server
After=network-online.target
Wants=network-online.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user
Environment="ARTIFACT_BUCKET=<BUCKET_NAME>"
Environment="AWS_REGION=us-east-1"
ExecStart=/home/ec2-user/income-api-venv/bin/python /home/ec2-user/src/serve.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable income-api
sudo systemctl cat income-api
exit
```

Chưa start service vì model chưa được pipeline upload. `Release` đầu tiên sẽ restart/start service.

---

## 7. GitHub Actions secrets

Repo -> **Settings -> Secrets and variables -> Actions** tạo đúng 6 secrets:

| Secret | Giá trị |
|---|---|
| `AWS_ACCESS_KEY_ID` | Access key của `day21msv01506` |
| `AWS_SECRET_ACCESS_KEY` | Secret key của `day21msv01506` |
| `ARTIFACT_BUCKET` | `amz01day21msv01506`, không có `s3://` |
| `SERVER_HOST` | `$VM_IP` |
| `SERVER_USER` | `ec2-user` |
| `SERVER_SSH_KEY` | Toàn bộ nội dung `$KEY_PATH` |

Copy private SSH key vào clipboard mà không in ra terminal:

```powershell
Get-Content -Raw $KEY_PATH | Set-Clipboard
```

Không chụp trang secret và không commit key.

---

## 8. Pipeline lần đầu và bằng chứng

### 8.1 Kiểm tra trước push

```powershell
pytest tests/ -v
python src/train.py
Get-Content outputs\report.json
git diff --check
git status --short
```

Xác nhận `params.yaml` đạt F1 >= 0.65; không stage CSV, model, report, `.venv` hay key.

```powershell
git add src tests .github/workflows/cicd.yml params.yaml requirements.txt .gitignore .dvc .dvcignore data/*.dvc plan.md
git diff --cached --name-only
git commit -m 'feat: complete AWS ML model CI/CD pipeline'
git push origin main
```

Vào tab Actions, chờ bốn job xanh. Tải artifact `report` và ghi F1/accuracy của **22.361 mẫu** vào báo cáo.

Chụp trang run có URL, commit message và bốn job xanh:

`nop-bai/anh-chup-man-hinh/02-actions-buoc-2.png`

### 8.2 Test API và chụp ảnh

```powershell
curl.exe "http://${VM_IP}:8080/healthz"
curl.exe -X POST "http://${VM_IP}:8080/score" -H 'Content-Type: application/json' -d '{"features":[60,2,5,2,4,0,1,0,0,45]}'
curl.exe -X POST "http://${VM_IP}:8080/score" -H 'Content-Type: application/json' -d '{"features":[28,2,14,2,11,0,1,0,0,45]}'
```

Chụp terminal có IP, healthz OK và score trả label hợp lệ:

`nop-bai/anh-chup-man-hinh/04-curl-api.png`

### 8.3 S3 screenshot

AWS Console -> **S3 -> `$BUCKET_NAME`**:

- Chụp prefix `dvc/`: `05a-storage-dvc.png`.
- Mở `artifacts/current/`, chụp `model.joblib`: `05b-storage-model.png`.

Ảnh phải có URL console và tên bucket.

---

## 9. Chứng minh Quality Gate chặn model yếu

Đổi `params.yaml` thành:

```yaml
n_estimators: 50
learning_rate: 0.05
max_depth: 2
```

```powershell
git add params.yaml
git commit -m 'test: verify quality gate blocks weak model'
git push origin main
```

Cần thấy Quality Gate đỏ vì F1 < 0.65 và Release skipped. Chụp:

`nop-bai/anh-chup-man-hinh/07-quality-gate-chan.png`

Khôi phục ngay bộ params tốt nhất, commit/push và chờ bốn job xanh lại:

```powershell
git add params.yaml
git commit -m 'fix: restore production model parameters'
git push origin main
```

Không làm bước dữ liệu mới trước khi run phục hồi thành công.

---

## 10. Commit dữ liệu kích hoạt Continuous Training

Kiểm tra số mẫu trước:

```powershell
(Import-Csv data\train_batch1.csv).Count
```

Chỉ khi kết quả là `22361`:

```powershell
python append_batch.py
(Import-Csv data\train_batch1.csv).Count
```

Kết quả phải là `44722`. Thực hiện đúng thứ tự:

```powershell
dvc add data/train_batch1.csv
git add data/train_batch1.csv.dvc
git diff --cached --name-only
git commit -m 'data: bổ sung 22361 mẫu dữ liệu mới (train_batch2)'
dvc push
git push origin main
```

`dvc push` bắt buộc thành công trước `git push`. Sau Git push, không train/restart/upload thủ công.

Trong Actions, mở đúng run có commit dữ liệu, chờ bốn job xanh rồi chụp:

`nop-bai/anh-chup-man-hinh/03-actions-buoc-3.png`

Tải report của run này để lấy F1/accuracy của **44.722 mẫu**. Gọi lại `/healthz` và `/score`.

---

## 11. Hoàn thiện báo cáo và nộp bài

Điền `nop-bai/bao-cao.md` bằng số thật:

1. Ba run MLflow và bộ params tốt nhất theo F1.
2. Vì sao gate dùng F1: lớp dương chỉ 24,8%; đoán toàn lớp thấp vẫn accuracy khoảng 0,752 nhưng F1 lớp dương bằng 0; F1 cân bằng precision/recall lớp cần phát hiện.
3. Khó khăn thật và cách giải quyết.
4. So sánh 22.361 với 44.722 mẫu; tăng/giảm nhẹ đều hợp lý vì hai batch cùng nguồn.

```powershell
(Get-Content -Raw nop-bai\bao-cao.md | Measure-Object -Word).Words
Get-ChildItem nop-bai\anh-chup-man-hinh
git status --short
```

Ảnh bắt buộc:

- `01-mlflow-ui.png`.
- `02-actions-buoc-2.png`.
- `03-actions-buoc-3.png`.
- `04-curl-api.png` hoặc `04a/04b`.
- `05-cloud-storage.png` hoặc `05a/05b`.
- `07-quality-gate-chan.png` để chứng minh gate.

```powershell
git add nop-bai plan.md
git diff --cached --name-only
git commit -m 'docs: add lab report and evidence'
git push origin main
```

Mở repo bằng cửa sổ ẩn danh, xác nhận Public và ảnh hiển thị. Nộp:

`https://github.com/Brianphams2/Track2_Day21_2A2022601506_PhamGiaBao`

---

## 12. Xử lý lỗi và kiểm soát chi phí

```powershell
aws s3 ls "s3://$BUCKET_NAME/dvc/" --recursive
aws s3 ls "s3://$BUCKET_NAME/artifacts/current/model.joblib"
ssh -i $KEY_PATH "ec2-user@$VM_IP" 'sudo journalctl -u income-api -n 100 --no-pager'
curl.exe "http://${VM_IP}:8080/healthz"
```

- DVC lỗi: kiểm tra local AWS identity và policy S3 của CI.
- GitHub Train lỗi auth: kiểm tra hai AWS secrets, không có dấu cách/dấu nháy thừa.
- Gate lỗi kiểu: ép output bằng `float()`.
- EC2 không SSH được: IP local có thể đã đổi; cập nhật ingress port 22.
- Service lỗi: kiểm tra IAM role gắn vào instance, bucket env và object model.
- API timeout: kiểm tra security group port 8080 và systemd log.

Sau khi nộp, stop EC2 để giảm chi phí:

```powershell
aws ec2 stop-instances --region us-east-1 --instance-ids $INSTANCE_ID
aws ec2 wait instance-stopped --region us-east-1 --instance-ids $INSTANCE_ID
```

Không xóa S3/model/ảnh trước khi chấm. Khi start lại, public IP có thể đổi; cập nhật `SERVER_HOST` nếu cần.

## Checklist hoàn thành

- [ ] AWS identity đúng, region mọi nơi là `us-east-1`.
- [ ] MLflow có >= 3 run, đủ params, F1 và accuracy.
- [ ] `pytest tests/ -v`: 3 passed.
- [ ] S3 có `dvc/` và `artifacts/current/model.joblib`.
- [ ] Pipeline lần đầu có bốn job xanh.
- [ ] Quality Gate từng chặn model yếu và skip Release.
- [ ] Commit dữ liệu duy nhất kích hoạt bốn job xanh.
- [ ] EC2 trả healthz OK và score có label hợp lệ.
- [ ] Đủ ảnh, báo cáo <= 1 trang, repo Public, không lộ secret.
