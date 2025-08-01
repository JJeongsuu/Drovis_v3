# core/services/predict.py

import os
import numpy as np
import torch
from core.services.save_analysis import save_analysis_result
from core.services.preprocess import process_pose
from core.config import Config
from core.models.lstm_model import LSTMModel

LABELS = ["상", "중", "하", "기타"]
MODEL_PATH = os.path.join(Config.MODEL_FOLDER, "lstm_model.pt")
UPLOAD_FOLDER = Config.UPLOAD_FOLDER

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = None
if os.path.exists(MODEL_PATH):
    model = LSTMModel()
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    model.to(device)
    model.eval()


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
        sequence = np.load(npy_path)
        input_tensor = (
            torch.tensor(sequence, dtype=torch.float32).unsqueeze(0).to(device)
        )
        with torch.no_grad():
            output = model(input_tensor)
            result_index = torch.argmax(output, dim=1).item()
            result_label = LABELS[result_index]
    except Exception as e:
        return {"success": False, "message": f"AI 예측 오류: {str(e)}"}

    try:
        save_analysis_result(user_id=user_id, filename=filename, result=result_label)
    except Exception as e:
        return {"success": False, "message": f"DB 저장 오류: {str(e)}"}

    return {
        "success": True,
        "filename": filename,
        "result": result_label,
        "npy_path": npy_path,
    }
