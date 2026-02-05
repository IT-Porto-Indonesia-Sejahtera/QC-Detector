import cv2
import csv
import os
import time
import xlsxwriter
from PySide6.QtCore import QThread, Signal, QObject
from model.measure_live_sandals import measure_live_sandals

class ConsistencyTestThread(QThread):
    """
    Runs consistency test by capturing N frames from the video thread
    and running measurement inference on them.
    Optionally saves images and exports to Excel.
    """
    progress_update = Signal(int, int) # current, total
    finished_test = Signal(str) # path to file (csv/xlsx)
    error_occurred = Signal(str)

    def __init__(self, video_thread, num_attempts=100, model_type='yolo', output_dir="output", mm_per_px=0.21, capture_images=False):
        super().__init__()
        self.video_thread = video_thread
        self.num_attempts = num_attempts
        self.model_type = model_type  # 'standard', 'yolo', 'sam'
        self.output_dir = output_dir
        self.mm_per_px = mm_per_px
        self.capture_images = capture_images
        self.current_count = 0
        self.results = []
        self.running = True
        self.is_connected = False
        
        # Temp dir for images if needed
        self.temp_img_dir = None
        if self.capture_images:
            timestamp = int(time.time())
            self.temp_img_dir = os.path.join(self.output_dir, f"temp_assets_{timestamp}")
            os.makedirs(self.temp_img_dir, exist_ok=True)

    def run(self):
        self.current_count = 0
        self.results = []
        self.running = True
        
        # Connect to video thread
        if self.video_thread:
            self.video_thread.frame_ready.connect(self.process_frame)
            self.is_connected = True
        else:
            self.error_occurred.emit("Video thread not available")
            return

        # Wait until finished
        while self.running and self.current_count < self.num_attempts:
            self.msleep(100)

        # Cleanup
        if self.is_connected:
            try:
                self.video_thread.frame_ready.disconnect(self.process_frame)
            except:
                pass
        
        if self.results:
            if self.capture_images:
                self.save_to_excel()
            else:
                self.save_to_csv()
        else:
            if self.running: # Only emit error if not manually stopped
                self.error_occurred.emit("No results collected")

    def process_frame(self, frame):
        if not self.running or self.current_count >= self.num_attempts:
            return

        try:
            # Determine flags based on model_type
            use_yolo = (self.model_type == 'yolo')
            use_sam = (self.model_type == 'sam')
            
            # Run measurement
            # Note: measure_live_sandals returns (results_list, processed_image)
            frame_results, processed_image = measure_live_sandals(
                frame, 
                mm_per_px=self.mm_per_px, 
                draw_output=True if self.capture_images else False, 
                use_yolo=use_yolo, 
                use_sam=use_sam
            )
            
            entry = {
                "attempt": self.current_count + 1,
                "timestamp": time.time(),
                "model": self.model_type,
                "objects_found": len(frame_results)
            }

            if self.capture_images and processed_image is not None:
                img_name = f"frame_{self.current_count + 1}.jpg"
                img_path = os.path.join(self.temp_img_dir, img_name)
                cv2.imwrite(img_path, processed_image)
                entry["image_path"] = img_path

            if frame_results:
                # Take the first (largest) result
                r = frame_results[0]
                entry.update(r)
            else:
                # Fill with None/Zeros if detection failed
                entry.update({
                    "px_length": 0, "px_width": 0,
                    "real_length_mm": 0, "real_width_mm": 0,
                    "pass_fail": "FAIL", "inference_time_ms": 0
                })

            self.results.append(entry)
            self.current_count += 1
            self.progress_update.emit(self.current_count, self.num_attempts)
            
            if self.current_count >= self.num_attempts:
                self.running = False

        except Exception as e:
            print(f"[ConsistencyTest] Error processing frame: {e}")
            self.running = False
            self.error_occurred.emit(str(e))

    def save_to_csv(self):
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                
            timestamp = int(time.time())
            filename = f"consistency_test_{self.model_type}_{timestamp}.csv"
            filepath = os.path.join(self.output_dir, filename)
            
            if not self.results:
                return

            keys = self.results[0].keys()
            
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(self.results)
                
            print(f"[ConsistencyTest] Saved to {filepath}")
            self.finished_test.emit(filepath)

        except Exception as e:
            self.error_occurred.emit(f"Failed to save CSV: {e}")

    def save_to_excel(self):
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                
            timestamp = int(time.time())
            filename = f"consistency_test_{self.model_type}_{timestamp}.xlsx"
            filepath = os.path.join(self.output_dir, filename)
            
            if not self.results:
                return

            workbook = xlsxwriter.Workbook(filepath)
            worksheet = workbook.add_worksheet("Consistency Test")
            
            # Formats
            bold = workbook.add_format({'bold': True, 'align': 'center', 'border': 1, 'bg_color': '#D3D3D3'})
            center = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
            
            # Define Headers
            headers = [
                "Attempt", "Timestamp", "Model", "Objects Found", 
                "PX Length", "PX Width", "Real Length (mm)", "Real Width (mm)", 
                "Pass/Fail", "Inference (ms)", "Image"
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, bold)
            
            # Row height for images
            row_height = 80
            worksheet.set_column('K:K', 20) # Image column width
            
            for i, res in enumerate(self.results):
                row = i + 1
                worksheet.set_row(row, row_height)
                
                worksheet.write(row, 0, res.get("attempt"), center)
                worksheet.write(row, 1, res.get("timestamp"), center)
                worksheet.write(row, 2, res.get("model"), center)
                worksheet.write(row, 3, res.get("objects_found"), center)
                worksheet.write(row, 4, res.get("px_length", 0), center)
                worksheet.write(row, 5, res.get("px_width", 0), center)
                worksheet.write(row, 6, res.get("real_length_mm", 0), center)
                worksheet.write(row, 7, res.get("real_width_mm", 0), center)
                worksheet.write(row, 8, res.get("pass_fail", "FAIL"), center)
                worksheet.write(row, 9, res.get("inference_time_ms", 0), center)
                
                # Insert Image
                if self.capture_images and "image_path" in res:
                    img_path = res["image_path"]
                    if os.path.exists(img_path):
                        # Scale image to fit row height roughly
                        # We don't want it too big. Row height 80 is ~106 pixels.
                        worksheet.insert_image(row, 10, img_path, {
                            'x_scale': 0.15, 
                            'y_scale': 0.15,
                            'x_offset': 5,
                            'y_offset': 5,
                            'object_position': 1
                        })

            workbook.close()
            print(f"[ConsistencyTest] Saved Excel to {filepath}")
            self.finished_test.emit(filepath)

        except Exception as e:
            self.error_occurred.emit(f"Failed to save Excel: {e}")
            import traceback
            traceback.print_exc()

    def stop(self):
        self.running = False
