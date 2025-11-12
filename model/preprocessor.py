import cv2
import numpy as np
import os

def ensure_dir(path):
    if path and not os.path.exists(path):
        os.makedirs(path)

def display_resized(img, max_height=800, window_name="Output"):
    if img.shape[0] > max_height:
        scale = max_height / img.shape[0]
        img = cv2.resize(img, None, fx=scale, fy=scale)
    cv2.imshow(window_name, img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def preprocess_and_masks(img_gray):
    blur = cv2.GaussianBlur(img_gray, (7,7), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9,9))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=3)
    return closed
