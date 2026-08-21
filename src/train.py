import mlflow
import mlflow.sklearn
import pandas as pd
import numpy as np
import yaml
import json
import joblib
import os
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    confusion_matrix,
    precision_recall_fscore_support,
)

# Nguong chat luong cua lab nay la f1_score, KHONG phai accuracy.
# Ly do: bo du lieu Adult co ty le lop 75/25. Mot mo hinh doan bua
# "thu nhap thap" cho moi mau da dat accuracy 0.75 ma khong hoc duoc gi.
F1_THRESHOLD = 0.65

# Bonus 5 - Canh bao lech lac du lieu.
# Ty le lop duong tham chieu cua bo Adult goc la 24.8%.
REFERENCE_POSITIVE_RATE = 0.248
DRIFT_TOLERANCE = 0.05  # 5 diem phan tram

# Bonus 2 - Dieu chinh nguong quyet dinh.
THRESHOLD_MIN = 0.10
THRESHOLD_MAX = 0.90
THRESHOLD_STEP = 0.05

DETAIL_PATH = "outputs/detail.txt"


def check_class_balance(y_train) -> float:
    """
    Bonus 5: kiem tra phan phoi lop truoc khi huan luyen.

    In canh bao ro rang neu ty le lop duong lech qua DRIFT_TOLERANCE so voi
    ty le tham chieu 24.8% cua bo du lieu goc.

    Tra ve:
        positive_rate (float): ty le lop duong trong tap huan luyen.
    """
    positive_rate = float(np.mean(y_train))
    drift = abs(positive_rate - REFERENCE_POSITIVE_RATE)

    if drift > DRIFT_TOLERANCE:
        print(
            f"[DRIFT] CANH BAO: ty le lop duong = {positive_rate:.4f}, "
            f"lech {drift * 100:.2f} diem phan tram so voi tham chieu "
            f"{REFERENCE_POSITIVE_RATE:.4f} (nguong cho phep "
            f"{DRIFT_TOLERANCE * 100:.0f} diem). Kiem tra lai nguon du lieu."
        )
    else:
        print(
            f"[DRIFT] OK: ty le lop duong = {positive_rate:.4f}, "
            f"lech {drift * 100:.2f} diem phan tram so voi tham chieu "
            f"{REFERENCE_POSITIVE_RATE:.4f}."
        )

    return positive_rate


def sweep_threshold(model, X_eval, y_eval):
    """
    Bonus 2: quet nguong quyet dinh thay vi dung mac dinh 0.5 cua predict().

    Voi du lieu mat can bang, nguong 0.5 hiem khi toi uu cho F1 cua lop duong.
    Ham nay quet tu 0.10 den 0.90 (buoc 0.05) va tra ve nguong cho F1 cao nhat.

    Tra ve:
        (best_threshold, best_f1)
    """
    probs = model.predict_proba(X_eval)[:, 1]

    best_threshold = 0.5
    best_f1 = -1.0
    for raw in np.arange(THRESHOLD_MIN, THRESHOLD_MAX + 1e-9, THRESHOLD_STEP):
        threshold = round(float(raw), 2)
        f1_at_threshold = float(f1_score(y_eval, (probs >= threshold).astype(int)))
        if f1_at_threshold > best_f1:
            best_threshold = threshold
            best_f1 = f1_at_threshold

    return best_threshold, best_f1


def write_detail_report(y_eval, preds) -> None:
    """
    Bonus 3: ghi confusion matrix va precision/recall tung lop ra outputs/detail.txt.

    File nay duoc GitHub Actions luu lai bang actions/upload-artifact cung report.json.
    """
    cm = confusion_matrix(y_eval, preds, labels=[0, 1])
    precision, recall, f1_per_class, support = precision_recall_fscore_support(
        y_eval, preds, labels=[0, 1], zero_division=0
    )

    names = {0: "thu_nhap_thap (0)", 1: "thu_nhap_cao  (1)"}
    lines = [
        "BAO CAO CHI TIET TREN TAP HOLDOUT",
        "=" * 52,
        "",
        "Confusion matrix (hang = thuc te, cot = du doan):",
        f"{'':>22}{'du doan 0':>12}{'du doan 1':>12}",
        f"{'thuc te 0':>22}{cm[0][0]:>12}{cm[0][1]:>12}",
        f"{'thuc te 1':>22}{cm[1][0]:>12}{cm[1][1]:>12}",
        "",
        f"{'Lop':<22}{'precision':>12}{'recall':>12}{'f1':>10}{'support':>10}",
        "-" * 66,
    ]
    for idx in (0, 1):
        lines.append(
            f"{names[idx]:<22}{precision[idx]:>12.4f}{recall[idx]:>12.4f}"
            f"{f1_per_class[idx]:>10.4f}{support[idx]:>10}"
        )
    lines.append("")
    lines.append(
        f"Bo sot lop duong (false negative): {cm[1][0]} | "
        f"Bao dong nham (false positive): {cm[0][1]}"
    )
    lines.append("")

    content = "\n".join(lines)
    os.makedirs("outputs", exist_ok=True)
    with open(DETAIL_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(content)


def train(
    params: dict,
    data_path: str = "data/train_batch1.csv",
    eval_path: str = "data/holdout.csv",
) -> float:
    """
    Huan luyen mo hinh va ghi nhan ket qua vao MLflow.

    Tham so:
        params     : dict chua cac sieu tham so cho GradientBoostingClassifier.
        data_path  : duong dan den file du lieu huan luyen.
        eval_path  : duong dan den file du lieu danh gia (holdout).

    Tra ve:
        f1 (float): diem F1 cua lop duong (thu nhap > 50K) tren tap holdout,
                    tinh tai nguong mac dinh 0.5. Day la con so quality gate dung.
    """

    df_train = pd.read_csv(data_path)
    df_eval = pd.read_csv(eval_path)

    X_train = df_train.drop(columns=["target"])
    y_train = df_train["target"]
    X_eval = df_eval.drop(columns=["target"])
    y_eval = df_eval["target"]

    # Bonus 5: kiem tra phan phoi TRUOC khi huan luyen.
    positive_rate = check_class_balance(y_train)

    # Bonus 1: MLflow doc MLFLOW_TRACKING_URI tu bien moi truong. De trong thi ghi
    # cuc bo; tro den https://dagshub.com/<user>/<repo>.mlflow thi ghi len server tu xa.
    print(f"[MLFLOW] Tracking URI: {mlflow.get_tracking_uri()}")

    with mlflow.start_run():

        mlflow.log_params(params)

        model = GradientBoostingClassifier(**params, random_state=42)
        model.fit(X_train, y_train)

        preds = model.predict(X_eval)
        f1 = float(f1_score(y_eval, preds))
        acc = float(accuracy_score(y_eval, preds))

        # Bonus 2: nguong quyet dinh toi uu tren tap holdout.
        best_threshold, f1_at_best_threshold = sweep_threshold(model, X_eval, y_eval)

        mlflow.log_metric("f1_score", f1)
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("positive_rate", positive_rate)
        mlflow.log_metric("best_threshold", best_threshold)
        mlflow.log_metric("f1_at_best_threshold", f1_at_best_threshold)

        # Cac chi so va tham so o tren la bat buoc, loi thi phai dung pipeline.
        # Rieng viec upload artifact model len tracking server la phan quan sat,
        # khong phai san pham giao di: san pham la models/model.joblib duoc
        # publish len S3 o job Release. Mot tracking server tu xa bi gioi han
        # dung luong hay chap chon khong duoc phep lam hong ca lan huan luyen.
        try:
            mlflow.sklearn.log_model(model, "model")
        except Exception as exc:  # noqa: BLE001
            print(f"[MLFLOW] Bo qua log_model (khong anh huong pipeline): {exc}")

        print(f"F1: {f1:.4f} | Accuracy: {acc:.4f}")
        print(
            f"[THRESHOLD] Nguong tot nhat {best_threshold:.2f} -> "
            f"F1 {f1_at_best_threshold:.4f} (nguong mac dinh 0.50 -> F1 {f1:.4f}, "
            f"chenh lech {f1_at_best_threshold - f1:+.4f})"
        )

        # Bonus 3: confusion matrix va precision/recall tung lop.
        write_detail_report(y_eval, preds)

        os.makedirs("outputs", exist_ok=True)
        with open("outputs/report.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "f1_score": f1,
                    "accuracy": acc,
                    "positive_rate": positive_rate,
                    "best_threshold": best_threshold,
                    "f1_at_best_threshold": f1_at_best_threshold,
                },
                f,
                indent=2,
            )

        os.makedirs("models", exist_ok=True)
        joblib.dump(model, "models/model.joblib")

    return f1


if __name__ == "__main__":
    with open("params.yaml") as f:
        params = yaml.safe_load(f)
    train(params)
