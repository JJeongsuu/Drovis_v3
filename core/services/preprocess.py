# core/services/preprocess.py
import cv2
import numpy as np
import mediapipe as mp


def process_pose(
    video_path,
    detected_points=33,
    return_stats=True,
):
    """
    영상에서 Pose 좌표를 추출해 (N, detected_points*2) 배열 반환.
    - 자르지 않음. (원본 길이 유지)
    - return_stats=True면 {"success":성공프레임, "fail":실패프레임}도 함께 반환.
    """
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
        static_image_mode=False, 
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
        )
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
            coords = []
            for lm in results.pose_landmarks.landmark:
                coords.extend([lm.x, lm.y])
            frames.append(coords)
            success_cnt += 1
        else:
            fail_cnt += 1
            continue

    cap.release()
    pose.close()

    frames = np.asarray(frames, dtype=np.float32)  # (N, 66)

    if return_stats:
        return frames, {"success": success_cnt, "fail": fail_cnt}
    return frames
