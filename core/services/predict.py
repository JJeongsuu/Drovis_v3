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
    # 0) 입력 체크
    if not os.path.isfile(video_path):
        return {"success": False, "message": f"영상 파일이 존재하지 않습니다: {video_path}"}

    filename = os.path.basename(video_path)
    npy_name = os.path.splitext(filename)[0] + ".pipe_norm_padd.npy"
    npy_path = os.path.join(UPLOAD_FOLDER, npy_name)

    # 1) 포즈 전처리 → npy 저장
    try:
        # process_pose가 (ndarray, stats) 또는 ndarray 둘 중 하나를 반환하더라도 처리
        proc_out = process_pose(video_path)
        if isinstance(proc_out, tuple):
            sequence_array, pose_stats = proc_out
        else:
            sequence_array = proc_out
            pose_stats = {"success": int(len(sequence_array)) if sequence_array is not None else 0, "fail": 0}

        if sequence_array is None or len(sequence_array) == 0:
            return {"success": False, "message": "MediaPipe pose 변환 실패"}

        # 필요하면 저장 (디버그/재현용)
        np.save(npy_path, sequence_array)
    except Exception as e:
        return {"success": False, "message": f"전처리 오류: {str(e)}"}

    # 2) 모델 체크
    if model is None:
        return {"success": False, "message": "AI 모델 파일이 없습니다."}

    # 3) 예측
    try:
        # 굳이 다시 로드하지 않고 바로 사용해도 됨
        sequence = sequence_array  # np.load(npy_path) 대신
        if len(sequence) < 30:
            return {
                "success": False,
                "message": f"입력 포즈 시퀀스 길이가 부족합니다. ({len(sequence)}프레임 < 30)",
            }

        # 슬라이딩 윈도우 (window=30, step=15)
        def split_sequence(seq, window=30, step=15):
            return [seq[i:i + window] for i in range(0, len(seq) - window + 1, step)]

        chunks = split_sequence(sequence)
        predictions = []

        for chunk in chunks:
            input_tensor = torch.tensor(chunk, dtype=torch.float32).unsqueeze(0).to(device)  # (1, 30, 66)
            with torch.no_grad():
                output = model(input_tensor)                   # (1, num_classes)
                pred_label = int(torch.argmax(output, dim=1))  # 정수 라벨
                predictions.append(pred_label)

        label_counts = Counter(predictions)

        # 3-1) 포즈 성공/실패 (process_pose가 stats를 주지 않았다면 위에서 len으로 채움)
        if not isinstance(pose_stats, dict):
            pose_stats = {"success": int(len(sequence)), "fail": 0}

        # 3-2) 행동 카운트 — 항상 0 포함(키 누락 방지)
        behavior_counts = {
            "Loitering": int(label_counts.get(1, 0)),
            "Delivery":  int(label_counts.get(2, 0)),  # ← handover 아님! LABEL_MAP과 통일
            "Reapproach": int(label_counts.get(3, 0)),
        }

        # 3-3) 위험도 산정
        suspicion_level = get_suspicion_level(label_counts)

        # 로그 (선택)
        total = sum(label_counts.values()) or 1
        print(f"\n포즈 인식 성공: {pose_stats.get('success', 0)}프레임 / 실패: {pose_stats.get('fail', 0)}프레임")
        print("\n예측된 행동 라벨 비율:")
        for label in sorted(label_counts):
            name = LABEL_MAP.get(label, str(label))
            count = label_counts[label]
            percent = (count / total) * 100
            print(f"- {name} (라벨 {label}): {count}회 ({percent:.2f}%)")

        detected = [LABEL_MAP[l] for l in SUSPICIOUS_LABELS if label_counts.get(l, 0) > 0]
        print(f"\n행동 탐지 결과 : {suspicion_level} ({', '.join(detected) if detected else '탐지 없음'})")

    except Exception as e:
        return {"success": False, "message": f"AI 예측 오류: {str(e)}"}

    # 4) 결과 저장 (DB 등) — 실패해도 작동 계속
    try:
        save_analysis_result(user_id=user_id, filename=filename, result=suspicion_level)
    except Exception as e:
        print(f"[경고] DB 저장 오류: {e}")

    # 5) 최종 반환(History에 필요한 필드 모두 포함)
    return {
        "success": True,
        "filename": filename,
        "result": suspicion_level,                              # 위험도(상/중/하)
        "pose_stats": pose_stats,                               # 포즈 인식 성공/실패
        "behavior_counts": behavior_counts,                     # 탐지 행동 비율(0 포함)
        "detected_actions": detected,                           # 참고용
        "result_per_chunk": [LABEL_MAP[p] for p in predictions],
        "npy_path": npy_path,
    }
