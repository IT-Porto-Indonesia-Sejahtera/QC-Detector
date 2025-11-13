import cv2
import os
from datetime import datetime
import numpy as np
from model.preprocessor import preprocess_and_masks, ensure_dir, display_resized
from model.measurement import endpoints_via_minrect, find_largest_contours

VIDEO_PATH = "QC-Detector\\input\\temp_assets\\sandal_simulasi.avi"   # ganti sesuai file kamu
OUTPUT_DIR = "QC-Detector\\output\\video_frames"
VIDEO_OUTPUT_DIR = "QC-Detector\\output\\video"
mm_per_px = None 
MIN_CONTOUR_AREA = 1000
DISPLAY_MAX_HEIGHT = 700
SAVE_FRAMES = True 
SAVE_VIDEO = True 

def draw_measure_overlay(img, box, px_length, px_width):
    out = img.copy()
    cv2.drawContours(out, [box], 0, (0,255,0), 2)
    center = tuple(np.mean(box, axis=0).astype(int))
    text = f"L={px_length:.1f}px W={px_width:.1f}px"
    cv2.putText(out, text, (center[0]-100, center[1]-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2, cv2.LINE_AA)
    return out

def main():
    ensure_dir(OUTPUT_DIR)

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print(f"Gagal membuka video: {VIDEO_PATH}")
        return
    fourcc = cv2.VideoWriter_fourcc(*'XVID')  # codec .avi
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_out_path = os.path.join(VIDEO_OUTPUT_DIR, f"processed_{timestamp}.avi")
    out_writer = cv2.VideoWriter(video_out_path, fourcc, fps, (width, height)) if SAVE_VIDEO else None

    frame_idx = 0
    all_results = []

    print("Memulai pemrosesan video...")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Video selesai dibaca.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mask = preprocess_and_masks(gray)
        contours = find_largest_contours(mask, num_contours=1)

        frame_result = {
            "frame": frame_idx,
            "px_length": None,
            "px_width": None,
            "real_length_mm": None,
            "real_width_mm": None
        }

        display_frame = frame.copy()
        if contours:
            cnt = contours[0]
            if cv2.contourArea(cnt) > MIN_CONTOUR_AREA:
                box, w, h, angle = endpoints_via_minrect(cnt)
                px_length = max(w, h)
                px_width = min(w, h)

                real_length = px_length * mm_per_px if mm_per_px else None
                real_width = px_width * mm_per_px if mm_per_px else None

                display_frame = draw_measure_overlay(frame, box, px_length, px_width)

                frame_result.update({
                    "px_length": float(px_length),
                    "px_width": float(px_width),
                    "real_length_mm": float(real_length) if real_length else None,
                    "real_width_mm": float(real_width) if real_width else None
                })

        all_results.append(frame_result)

        if display_frame.shape[0] > DISPLAY_MAX_HEIGHT:
            scale = DISPLAY_MAX_HEIGHT / display_frame.shape[0]
            show = cv2.resize(display_frame, None, fx=scale, fy=scale)
        else:
            show = display_frame
        cv2.imshow("Video QC Simulation", show)

        if SAVE_FRAMES:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            fname = os.path.join(OUTPUT_DIR, f"frame_{frame_idx:04d}_{ts}.png")
            cv2.imwrite(fname, display_frame)
        
        if SAVE_VIDEO:
            out_writer.write(display_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("Dihentikan oleh user.")
            break

        frame_idx += 1

    cap.release()
    cv2.destroyAllWindows()

    print("\nHasil pengukuran per frame:")
    for r in all_results:
        print(r)

if __name__ == "__main__":
    main()
