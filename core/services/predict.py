import os
import numpy as np
import torch
from collections import Counter
from core.services.save_analysis import save_analysis_result
from core.services.preprocess import process_pose
from core.config import Config
from core.models.lstm_model import LSTMModel

LABEL_MAP = {0: "Normal", 1: "Loitering", 2: "Delivery", 3: "Reapproach"}
SUSPICIOUS_LABELS = {1, 2, 3}

MODEL_PATH = os.path.join(Config.MODEL_FOLDER, "lstm_model.pt")
UPLOAD_FOLDER = Config.UPLOAD_FOLDER

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 모델 로드
model = None
if os.path.exists(MODEL_PATH):
    model = LSTMModel()
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    model.to(device)
    model.eval()


def get_suspicion_level(label_counts: Counter) -> str:
    total = sum(label_counts.values())
    percent = {
        LABEL_MAP[label]: (count / total) * 100
        for label, count in label_counts.items()
        if label in SUSPICIOUS_LABELS
    }

    loitering = percent.get("Loitering", 0)
    reapproach = percent.get("Reapproach", 0)
    delivery = percent.get("Delivery", 0)

    if max(loitering, reapproach, delivery) >= 90:
        return "상"
    if loitering >= 60 and reapproach >= 60:
        return "중"
    if (loitering + reapproach + delivery) >= 50:
        return "중"
    return "하"


def predict_from_video(video_path: str, user_id: str) -> dict:
    if not os.path.isfile(video_path):
        return {
            "success": False,
            "message": f"영상 파일이 존재하지 않습니다: {video_path}",
        }

    filename = os.path.basename(video_path)
    npy_name = os.path.splitext(filename)[0] + ".pipe_norm_padd.npy"
    npy_path = os.path.join(UPLOAD_FOLDER, npy_name)

    try:
        sequence_array = process_pose(video_path)
        if sequence_array is None:
            return {"success": False, "message": "MediaPipe pose 변환 실패"}
        np.save(npy_path, sequence_array)
    except Exception as e:
        return {"success": False, "message": f"전처리 오류: {str(e)}"}

    if model is None:
        return {"success": False, "message": "AI 모델 파일이 없습니다."}

    try:
        sequence = np.load(npy_path)  # shape: (N, 66)
        if len(sequence) < 30:
            return {
                "success": False,
                "message": f"입력 포즈 시퀀스 길이가 부족합니다. ({len(sequence)}프레임 < 30)",
            }

        # 시퀀스를 슬라이딩 윈도우로 분할
        def split_sequence(seq, window=30, step=15):
            return [seq[i : i + window] for i in range(0, len(seq) - window + 1, step)]

        chunks = split_sequence(sequence)

        predictions = []

        for chunk in chunks:
            input_tensor = (
                torch.tensor(chunk, dtype=torch.float32).unsqueeze(0).to(device)
            )
            with torch.no_grad():
                output = model(input_tensor)
                pred_label = torch.argmax(output, dim=1).item()
                predictions.append(pred_label)

        label_counts = Counter(predictions)
        suspicion_level = get_suspicion_level(label_counts)

        # 분석 로그 출력
        print(f"\n포즈 인식 성공: {len(sequence)}프레임 / 실패: 0프레임")
        print("\n예측된 행동 라벨 비율:")
        total = sum(label_counts.values())
        for label in sorted(label_counts):
            name = LABEL_MAP[label]
            count = label_counts[label]
            percent = (count / total) * 100
            print(f"- {name} (라벨 {label}): {count}회 ({percent:.2f}%)")

        detected = [
            LABEL_MAP[l] for l in SUSPICIOUS_LABELS if label_counts.get(l, 0) > 0
        ]
        detected_str = ", ".join(detected)
        print(f"\n행동 탐지 결과 : {suspicion_level} ({detected_str})")

    except Exception as e:
        return {"success": False, "message": f"AI 예측 오류: {str(e)}"}

    try:
        save_analysis_result(user_id=user_id, filename=filename, result=suspicion_level)
    except Exception as e:
        return {"success": False, "message": f"DB 저장 오류: {str(e)}"}

    return {
        "success": True,
        "filename": filename,
        "result": suspicion_level,
        "detected_actions": detected,
        "result_per_chunk": [LABEL_MAP[p] for p in predictions],
        "npy_path": npy_path,
    }
