import cv2
import sys
import os
import glob
import base64
import time
import signal
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from model.measure_live_sandals import measure_live_sandals
from model.measurement import measure_sandals

# We'll use a global to keep track of the camera so we can release it
camera_holder = {"cap": None}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    if camera_holder["cap"]:
        camera_holder["cap"].release()
    print("Camera released.")

app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helpers
INPUT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../input/temp_assets'))
OUTPUT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../output/log_output'))
DATASET_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../output/dataset'))

os.makedirs(INPUT_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(DATASET_FOLDER, exist_ok=True)

# Mount static files
app.mount("/gallery_files", StaticFiles(directory=INPUT_FOLDER), name="gallery")
app.mount("/output_files", StaticFiles(directory=OUTPUT_FOLDER), name="output")

# --- Global State for Live View ---
latest_result = {}

def get_camera_source():
    for i in range(2):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret: return cap
            cap.release()
    return None

async def generate_frames(camera_idx=None):
    global latest_result
    if camera_holder["cap"] is None:
        camera_holder["cap"] = cv2.VideoCapture(camera_idx) if camera_idx is not None else get_camera_source()
    
    cap = camera_holder["cap"]
    if not cap or not cap.isOpened():
        return

    mm_per_px = 0.215984148 

    try:
        while True:
            success, frame = cap.read()
            if not success: break

            try:
                results, processed_frame = measure_live_sandals(frame.copy(), mm_per_px=mm_per_px, draw_output=True)
                
                # Draw timestamp for verification
                bold_font = cv2.FONT_HERSHEY_SIMPLEX
                cv2.putText(processed_frame, f"LIVE {time.time():.2f}", (10, 30), bold_font, 1, (0, 255, 0), 2)

                # Convert to Base64 for WebSocket (Snapshot view)
                _, buffer = cv2.imencode('.jpg', processed_frame)
                b64_image = base64.b64encode(buffer).decode('utf-8')
                
                # Update global state
                latest_result = {
                    "pass_fail": "PASS" if (results and results[0].get("px_length")) else "IDLE",
                    "real_length_mm": results[0].get("real_length_mm") if results else 0,
                    "real_width_mm": results[0].get("real_width_mm") if results else 0,
                    "image": b64_image
                }

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            except Exception:
                pass
            await asyncio.sleep(0.01)
    finally:
        pass

@app.get("/video_feed")
def video_feed(camera_index: int = None):
    return StreamingResponse(generate_frames(camera_index), media_type="multipart/x-mixed-replace;boundary=frame")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(latest_result)
            await asyncio.sleep(0.1) 
    except Exception:
        pass

@app.get("/gallery")
def list_gallery_images():
    files = glob.glob(os.path.join(INPUT_FOLDER, "*.*"))
    return [{"name": os.path.basename(f), "url": f"/gallery_files/{os.path.basename(f)}"} 
            for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

class MeasureRequest(BaseModel):
    filename: str

@app.post("/measure/photo")
def measure_photo(req: MeasureRequest):
    input_path = os.path.join(INPUT_FOLDER, req.filename)
    if not os.path.exists(input_path): raise HTTPException(status_code=404, detail="File not found")
    output_filename = f"measured_{int(time.time())}.png"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    try:
        results, _ = measure_sandals(input_path, mm_per_px=None, draw_output=False, save_out=output_path)
        return {"success": True, "results": results, "output_url": f"/output_files/{output_filename}"}
    except Exception as e: return {"success": False, "error": str(e)}

@app.get("/cameras")
def list_cameras():
    cams = []
    for i in range(3):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cams.append(i); cap.release()
    return cams

@app.post("/dataset/capture")
def capture_dataset(camera_index: int = 0):
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened(): raise HTTPException(status_code=500, detail="Camera unavailable")
    ret, frame = cap.read(); cap.release()
    if not ret: raise HTTPException(status_code=500, detail="Failed to capture")
    filename = f"dataset_{int(time.time()*1000)}.jpg"
    filepath = os.path.join(DATASET_FOLDER, filename)
    cv2.imwrite(filepath, frame)
    return {"success": True, "filename": filename, "path": filepath}

@app.post("/shutdown")
async def shutdown_server():
    async def delayed_exit():
        await asyncio.sleep(0.5)
        os.kill(os.getpid(), signal.SIGINT)
    asyncio.create_task(delayed_exit())
    return {"message": "Shutting down..."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
