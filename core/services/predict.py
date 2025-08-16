import os
import numpy as np
import torch
import math
from collections import Counter

# 지우기 from core.services.save_analysis import save_analysis_result
from core.services.preprocess import process_pose
from core.config import Config
from core.models.lstm_model import LSTMModel

DEBUG = True  # 개발 중엔 True, 운영에서는 False


PELVIS_L, PELVIS_R = 23, 24
SHOULDER_L, SHOULDER_R = 11, 12


def normalize_seq_2d(seq: np.ndarray) -> np.ndarray:
    """
    seq: (T, 66)  # (33개 포인트 × x,y)
    골반 중심 정렬 + 상체 길이 스케일링
    """
    if seq.ndim != 2 or seq.shape[1] != 66:
        return seq.astype(np.float32)

    out = np.zeros_like(seq, dtype=np.float32)
    for t, fr in enumerate(seq):
        kp = fr.reshape(33, 2).astype(np.float32)
        pelvis = (kp[PELVIS_L] + kp[PELVIS_R]) / 2.0
        shoulder_y = (kp[SHOULDER_L, 1] + kp[SHOULDER_R, 1]) / 2.0
        torso_h = abs(pelvis[1] - shoulder_y)
        if torso_h < 1e-6:
            torso_h = 1.0
        out[t] = ((kp - pelvis) / torso_h).flatten()
    return out


LABEL_MAP = {0: "Normal", 1: "Loitering", 2: "Handover", 3: "Reapproach"}
SUSPICIOUS_LABELS = {1, 2, 3}

MODEL_PATH = os.path.join(Config.MODEL_FOLDER, "lstm_model.pt")
UPLOAD_FOLDER = Config.UPLOAD_FOLDER

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 모델 로드(모듈 import 시 1회)
model = None
if os.path.exists(MODEL_PATH):
    model = LSTMModel()
    state = torch.load(MODEL_PATH, map_location=device)
    model.load_state_dict(state)
    model.to(device)
    model.eval()
    torch.set_num_threads(1)


def get_suspicion_level(label_counts: Counter, *, min_total_chunks: int = 4) -> str:
    total = sum(label_counts.values())
    if total == 0 or total < min_total_chunks:
        return "하"

    loitering = label_counts.get(1, 0)
    handover = label_counts.get(2, 0)
    reapproach = label_counts.get(3, 0)

    thr20 = math.ceil(0.20 * total)
    thr80 = math.ceil(0.80 * total)

    meets20 = [
        loitering >= thr20,
        handover >= thr20,
        reapproach >= thr20,
    ]
    cnt20 = sum(meets20)

    if cnt20 == 3:
        return "상"
    if cnt20 >= 2:
        return "중"
    if loitering >= thr80 or handover >= thr80 or reapproach >= thr80:
        return "중"
    if cnt20 == 1:
        return "하"
    return "하"


def predict_from_video(video_path: str, user_id: str) -> dict:
    # 0) 입력 체크
    if not os.path.isfile(video_path):
        return {
            "success": False,
            "message": f"영상 파일이 존재하지 않습니다: {video_path}",
        }

    filename = os.path.basename(video_path)
    # 정규화+패딩 결과를 저장한다는 의미에 맞춰 이름 유지
    npy_name = os.path.splitext(filename)[0] + ".pipe_norm_padd.npy"
    npy_path = os.path.join(UPLOAD_FOLDER, npy_name)

    # 1) 포즈 전처리 (stats 확실히 받도록)
    try:
        pose_seq, pose_stats = process_pose(
            video_path,
            detected_points=33,
            return_stats=True,
        )
        if pose_seq is None or len(pose_seq) == 0:
            return {"success": False, "message": "MediaPipe pose 변환 실패"}
    except Exception as e:
        return {"success": False, "message": f"전처리 오류: {str(e)}"}

    # 2) 모델 체크
    if model is None:
        return {"success": False, "message": "AI 모델 파일이 없습니다."}

    # 3) 예측
    try:
        # 정규화
        sequence = normalize_seq_2d(np.asarray(pose_seq, dtype=np.float32))

        # (옵션) 디버그/재현용 저장: 정규화된 시퀀스를 저장
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        np.save(npy_path, sequence)

        # 길이 체크(정규화 후에도 동일)
        if len(sequence) < 30:
            return {
                "success": False,
                "message": f"입력 포즈 시퀀스 길이가 부족합니다. ({len(sequence)}프레임 < 30)",
            }

        # 슬라이딩 윈도우
        def make_chunk_step(seq: np.ndarray, window: int = 30, step: int = 1):
            n = len(seq)
            return [seq[i:i+window] for i in range(0, n - window + 1, step)]

        chunks = make_chunk_step(sequence, window=30)
        if not chunks:
            return {
                "success": False,
                "message": f"윈도우가 생성되지 않았습니다. (frames={len(sequence)} < 30)",
            }

        predictions = []
        probs_list = []

        with torch.no_grad():
            for chunk in chunks:
                x = (
                    torch.from_numpy(np.asarray(chunk, dtype=np.float32))
                    .unsqueeze(0)
                    .to(device)
                )
                logits = model(x)

                probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
                pred_label = int(np.argmax(probs))
                predictions.append(pred_label)
                probs_list.append(probs)

        label_counts = Counter(predictions)

        # 포즈 통계 보정(혹시 None이면)
        if not isinstance(pose_stats, dict):
            pose_stats = {"success": int(len(sequence)), "fail": 0}

        avg = np.mean(np.vstack(probs_list), axis=0)
        behavior_probs_pct = {
            "Loitering": round(float(avg[1] * 100), 1),
            "Handover": round(float(avg[2] * 100), 1),
            "Reapproach": round(float(avg[3] * 100), 1),
        }

        # 위험도 산정
        suspicion_level = get_suspicion_level(label_counts)

        # ---------------------------
        # 로그 출력 (선택적)
        # ---------------------------
        if DEBUG:
            total = sum(label_counts.values()) or 1
            print(f"\n[INFO] 파일명: {filename}")
            print(
                f"포즈 인식 성공: {pose_stats.get('success', 0)} / 실패: {pose_stats.get('fail', 0)}"
            )

            print("\n예측된 행동 라벨 분포:")
            for label in sorted(label_counts):
                name = LABEL_MAP.get(label, str(label))
                count = label_counts[label]
                percent = (count / total) * 100
                print(f"- {name} (라벨 {label}): {count}회 ({percent:.2f}%)")

            detected = [
                LABEL_MAP[l] for l in SUSPICIOUS_LABELS if label_counts.get(l, 0) > 0
            ]
            print(
                f"\n행동 탐지 결과: {suspicion_level} "
                f"({', '.join(detected) if detected else '탐지 없음'})\n"
            )
            print(
                f"[DBG] frames(after norm)={len(sequence)}, chunks={len(chunks)}, expect={max(len(sequence)-29,0)}"
            )

        detected = [
            LABEL_MAP[l] for l in SUSPICIOUS_LABELS if label_counts.get(l, 0) > 0
        ]

    except Exception as e:
        return {"success": False, "message": f"AI 예측 오류: {str(e)}"}

    # 5) 최종 반환(History에 필요한 필드 모두 포함)
    return {
        "success": True,
        "filename": filename,
        "result": suspicion_level,  # 위험도(상/중/하)
        "pose_stats": pose_stats,  # 포즈 인식 성공/실패
        "behavior_probs_pct": behavior_probs_pct,  # 탐지 행동 '비율'(%) — 0 포함
        "behavior_counts":behavior_probs_pct,     # 프론트 수정 후 삭제 예정
        "detected_actions": detected,  # 참고용
        "result_per_chunk": [LABEL_MAP[p] for p in predictions],
        "npy_path": npy_path,
    }
