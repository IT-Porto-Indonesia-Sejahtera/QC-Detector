import cv2
import os
import project_utilities as putils
from datetime import datetime
from model.preprocessor import ensure_dir
from model.measurement_video import process_video

VIDEO_PATH = putils.normalize_path("QC-Detector\\input\\temp_assets\\sandal_simulasi.avi")
OUTPUT_DIR = putils.normalize_path("QC-Detector\\output\\video_frames")
VIDEO_OUTPUT_DIR = putils.normalize_path("QC-Detector\\output\\video")

mm_per_px = None
DISPLAY_MAX_HEIGHT = 700

SAVE_FRAMES = False
SAVE_VIDEO = False

VIDEO_MODE = "processed"  # pilih antara "raw" atau "processed"

def main():
    ensure_dir(OUTPUT_DIR)
    ensure_dir(VIDEO_OUTPUT_DIR)

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print(f"Gagal membuka video: {VIDEO_PATH}")
        return

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_out_path = os.path.join(VIDEO_OUTPUT_DIR, f"processed_{timestamp}.avi")
    out_writer = cv2.VideoWriter(video_out_path, fourcc, fps, (width, height)) if SAVE_VIDEO else None

    frame_idx = 0
    all_results = []

    print("Memulai pemrosesan video...\nTekan 'q' untuk berhenti.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Video selesai dibaca.")
            break

        results, processed_frame = process_video(
            frame,
            mm_per_px=mm_per_px,
            draw_output=False, 
            save_out=None
        )

        display_frame = frame if VIDEO_MODE == "raw" else processed_frame

        frame_result = {"frame": frame_idx, "results": results}
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

        if SAVE_VIDEO and out_writer:
            out_writer.write(display_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("Dihentikan oleh user.")
            break

        frame_idx += 1

    cap.release()
    if out_writer:
        out_writer.release()
    cv2.destroyAllWindows()

    print("\nHasil pengukuran per frame:")
    for r in all_results:
        print(r)

if __name__ == "__main__":
    main()
