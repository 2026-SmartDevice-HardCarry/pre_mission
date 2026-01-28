import cv2
import mediapipe as mp
import time
import numpy as np
import os

def load_sunglasses_with_alpha(image_path):
    """선글라스 이미지를 로드하고 흰색 배경을 제거하여 알파 채널 생성"""
    # 한글 경로 지원을 위해 numpy로 읽기
    with open(image_path, "rb") as f:
        file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_UNCHANGED)
    
    if img is None:
        print(f"Error: Could not load sunglasses image from {image_path}")
        return None
    
    # 알파 채널이 없으면 흰색 배경 제거
    if img.shape[2] == 3:
        # BGR to BGRA
        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        
        # 흰색/밝은 배경 제거 (임계값 기반)
        # 밝기가 높은 픽셀(흰색)을 투명하게
        gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
        
        # 흰색 배경 감지 (밝기 > 240)
        white_mask = gray > 240
        
        # 알파 채널 설정: 흰색 배경은 투명(0), 나머지는 불투명(255)
        img[:, :, 3] = np.where(white_mask, 0, 255).astype(np.uint8)
    else:
        # 이미 알파 채널이 있어도 흰색 배경 제거
        gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
        white_mask = gray > 240
        img[:, :, 3] = np.where(white_mask, 0, img[:, :, 3]).astype(np.uint8)
    
    return img

def overlay_image_alpha(background, overlay, x, y):
    """알파 채널을 이용한 이미지 오버레이"""
    h, w = overlay.shape[:2]
    bg_h, bg_w = background.shape[:2]
    
    # 경계 체크
    if x >= bg_w or y >= bg_h:
        return background
    if x + w <= 0 or y + h <= 0:
        return background
    
    # 오버레이 영역 계산 (화면 밖으로 나가는 부분 처리)
    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(bg_w, x + w)
    y2 = min(bg_h, y + h)
    
    # 오버레이 이미지에서의 해당 영역
    overlay_x1 = x1 - x
    overlay_y1 = y1 - y
    overlay_x2 = overlay_x1 + (x2 - x1)
    overlay_y2 = overlay_y1 + (y2 - y1)
    
    # 알파 블렌딩
    alpha = overlay[overlay_y1:overlay_y2, overlay_x1:overlay_x2, 3] / 255.0
    alpha = alpha[:, :, np.newaxis]
    
    roi = background[y1:y2, x1:x2]
    overlay_rgb = overlay[overlay_y1:overlay_y2, overlay_x1:overlay_x2, :3]
    
    # 블렌딩 공식: result = overlay * alpha + background * (1 - alpha)
    blended = (overlay_rgb * alpha + roi * (1 - alpha)).astype(np.uint8)
    background[y1:y2, x1:x2] = blended
    
    return background

def rotate_and_scale_image(img, angle, scale):
    """이미지 회전 및 크기 조절"""
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    
    # 회전 행렬
    M = cv2.getRotationMatrix2D(center, angle, scale)
    
    # 회전 후 이미지 크기 계산
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    new_w = int(h * sin + w * cos)
    new_h = int(h * cos + w * sin)
    
    # 회전 중심 조정
    M[0, 2] += (new_w - w) / 2
    M[1, 2] += (new_h - h) / 2
    
    # 회전 적용
    rotated = cv2.warpAffine(img, M, (new_w, new_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    
    return rotated

def main():
    # MediaPipe Tasks API 사용
    BaseOptions = mp.tasks.BaseOptions
    FaceLandmarker = mp.tasks.vision.FaceLandmarker
    FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
    RunningMode = mp.tasks.vision.RunningMode

    # 모델 파일을 바이트로 읽기 (한글 경로 문제 해결)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(script_dir, "face_landmarker.task")
    
    with open(model_path, "rb") as f:
        model_data = f.read()

    # 선글라스 이미지 로드
    sunglasses_path = os.path.join(script_dir, "sunglasses.png")
    sunglasses_img = load_sunglasses_with_alpha(sunglasses_path)
    if sunglasses_img is None:
        print("Error: Failed to load sunglasses image.")
        return

    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_buffer=model_data),
        running_mode=RunningMode.VIDEO,
        num_faces=5,  
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    # Open webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # For FPS calculation
    prev_time = 0
    
    # For printing control
    last_print_time = 0

    print("Press 'q' to exit.")

    with FaceLandmarker.create_from_options(options) as landmarker:
        while cap.isOpened():
            success, image = cap.read()
            if not success:
                print("Ignoring empty camera frame.")
                continue

            # Flip the image horizontally for selfie-view
            image = cv2.flip(image, 1)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            current_time = time.time()
            frame_timestamp_ms = int(current_time * 1000)

            # MediaPipe Tasks 형식으로 이미지 변환
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
            
            # 얼굴 랜드마크 감지
            result = landmarker.detect_for_video(mp_image, frame_timestamp_ms)

            # OpenCV 출력용 BGR로 다시 변환
            image = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)

            # 모든 감지된 얼굴에 선글라스 적용
            if result.face_landmarks:
                for face_landmarks in result.face_landmarks:
                    h, w, _ = image.shape

                    # 좌표 변환 함수
                    def to_px(lm):
                        return (int(lm.x * w), int(lm.y * h))
                    
                    # 눈 위치 추출 (외곽 포인트 사용)
                    left_eye_outer = to_px(face_landmarks[33])   # 왼쪽 눈 외곽
                    left_eye_inner = to_px(face_landmarks[133])  # 왼쪽 눈 내곽
                    right_eye_inner = to_px(face_landmarks[362]) # 오른쪽 눈 내곽
                    right_eye_outer = to_px(face_landmarks[263]) # 오른쪽 눈 외곽
                    
                    # 눈 중심점 계산
                    left_eye_center = to_px(face_landmarks[468])  # 왼쪽 홍채 중심
                    right_eye_center = to_px(face_landmarks[473]) # 오른쪽 홍채 중심
                    
                    # 두 눈 사이의 거리와 각도 계산
                    eye_distance = np.sqrt((right_eye_center[0] - left_eye_center[0])**2 + 
                                          (right_eye_center[1] - left_eye_center[1])**2)
                    
                    angle = np.degrees(np.arctan2(right_eye_center[1] - left_eye_center[1],
                                                   right_eye_center[0] - left_eye_center[0]))
                    
                    # 선글라스 크기 조절 비율 (눈 사이 거리에 맞춤)
                    # 선글라스 원본의 눈 간격 비율 기준
                    original_sunglasses_width = sunglasses_img.shape[1]
                    scale = (eye_distance * 2.5) / original_sunglasses_width
                    
                    # 선글라스 회전 및 크기 조절
                    transformed_sunglasses = rotate_and_scale_image(sunglasses_img, -angle, scale)
                    
                    # 선글라스 위치 계산 (두 눈 중심에 배치)
                    center_x = (left_eye_center[0] + right_eye_center[0]) // 2
                    center_y = (left_eye_center[1] + right_eye_center[1]) // 2
                    
                    # 선글라스 중심을 눈 중심에 맞춤
                    sunglasses_x = center_x - transformed_sunglasses.shape[1] // 2
                    sunglasses_y = center_y - transformed_sunglasses.shape[0] // 2
                    
                    # 선글라스 오버레이
                    image = overlay_image_alpha(image, transformed_sunglasses, sunglasses_x, sunglasses_y)

                    # 랜드마크 출력 (1초마다)
                    if current_time - last_print_time > 1.0:
                        nose_tip = face_landmarks[1]
                        print(f"Nose Tip: x={nose_tip.x:.4f}, y={nose_tip.y:.4f}, z={nose_tip.z:.4f}")
                        last_print_time = current_time

            # 결과 출력
            cv2.imshow('MediaPipe FaceMesh Filter', image)

            if cv2.waitKey(5) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
