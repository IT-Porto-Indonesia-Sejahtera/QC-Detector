import cv2
import os

image_folder = 'QC-Detector\\input\\temp_assets\\'
video_name = 'QC-Detector\\input\\temp_assets\\sandal_simulasi.avi'

images = [img for img in os.listdir(image_folder) if img.endswith((".jpeg", ".png"))]
images.sort()  

frame = cv2.imread(os.path.join(image_folder, images[0]))
height, width, layers = frame.shape

video = cv2.VideoWriter(video_name, cv2.VideoWriter_fourcc(*'XVID'), 5, (width, height))

for image in images:
    frame = cv2.imread(os.path.join(image_folder, image))
    video.write(frame)

video.release()
