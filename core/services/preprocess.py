# core/services/preprocess.py
import cv2
import numpy as np
import mediapipe as mp
import math

def process_pose(
    video_path,
    detected_points=33,
    return_stats=True,
    pad_to_step=False,   # 필요하면 True로
    step=15
):
    """
    영상에서 Pose 좌표를 추출해 (N, detected_points*2) 배열 반환.
    - 자르지 않음. (원본 길이 유지)
    - return_stats=True면 {"success":성공프레임, "fail":실패프레임}도 함께 반환.
    - pad_to_step=True면 길이를 step의 배수로 패딩(자르지는 않음).
    """
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5)
    cap = cv2.VideoCapture(video_path)
    frames = []
    success_cnt, fail_cnt = 0, 0

    if not cap.isOpened():
        print(f"[ERROR] 영상 파일을 열 수 없습니다: {video_path}")
        return (None, None) if return_stats else None

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(frame_rgb)
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            coords = []
            for lm in landmarks:
                coords.extend([lm.x, lm.y])
            frames.append(coords)
            success_cnt += 1
        else:
            # 실패 프레임은 0으로 채워서 넣어도 되고, 안 넣고 fail만 올려도 됨
            frames.append([0] * detected_points * 2)
            fail_cnt += 1

    cap.release()
    pose.close()

    frames = np.asarray(frames)  # (N, 66)

    # 필요하면 step 배수로만 패딩 (자르지 않음)
    if pad_to_step and len(frames) > 0:
        target = math.ceil(len(frames) / step) * step
        if target > len(frames):
            pad = np.tile(frames[-1], (target - len(frames), 1))
            frames = np.vstack([frames, pad])

    if return_stats:
        return frames, {"success": success_cnt, "fail": fail_cnt}
    return frames
