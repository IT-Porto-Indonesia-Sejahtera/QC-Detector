import cv2
import numpy as np

def endpoints_via_pca(contour):
    pts = contour.reshape(-1,2).astype(np.float32)
    if pts.shape[0] < 2:
        return None, None
    mean = pts.mean(axis=0)
    cov = np.cov((pts-mean).T)
    eigvals, eigvecs = np.linalg.eigh(cov)
    principal = eigvecs[:, np.argmax(eigvals)]
    proj = (pts - mean) @ principal
    min_idx = np.argmin(proj)
    max_idx = np.argmax(proj)
    return tuple(pts[min_idx].astype(int)), tuple(pts[max_idx].astype(int))

def split_by_vertical_valley(binary_mask):
    counts = (binary_mask>0).sum(axis=0)
    w = len(counts)
    start = w//3
    end = 2*w//3
    if end <= start:
        cut = w//2
    else:
        cut = np.argmin(counts[start:end]) + start
    left = binary_mask.copy()
    right = binary_mask.copy()
    left[:, cut:] = 0
    right[:, :cut] = 0
    return left, right, cut

def preprocess_and_masks(img_gray):
    blur = cv2.GaussianBlur(img_gray, (5,5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7,7))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    return closed

def find_largest_contour(mask):
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    cnts = sorted(cnts, key=lambda c: cv2.contourArea(c), reverse=True)
    return cnts[0]

def measure_sandals(path, mm_per_px=None, draw_output=True, save_out=None):
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mask = preprocess_and_masks(gray)

    left_mask, right_mask, cut_col = split_by_vertical_valley(mask)

    left_cnt = find_largest_contour(left_mask)
    right_cnt = find_largest_contour(right_mask)

    out = img.copy()
    results = []

    for cnt, side in [(left_cnt, 'left'), (right_cnt, 'right')]:
        if cnt is None:
            results.append({'side': side, 'found': False})
            continue
        p1, p2 = endpoints_via_pca(cnt)
        if p1 is None or p2 is None:
            results.append({'side': side, 'found': False})
            continue
        px_dist = np.linalg.norm(np.array(p1) - np.array(p2))
        real_dist = None
        if mm_per_px:
            real_dist = px_dist * mm_per_px

        cv2.circle(out, p1, 6, (0,0,255), -1)  
        cv2.circle(out, p2, 6, (0,255,0), -1)   
        cv2.line(out, p1, p2, (255,0,0), 2)

        results.append({
            'side': side,
            'found': True,
            'p1': p1,
            'p2': p2,
            'px_dist': float(px_dist),
            'real_dist_mm': float(real_dist) if real_dist is not None else None
        })

    cv2.line(out, (cut_col,0), (cut_col, out.shape[0]-1), (0,255,255), 1)

    if draw_output:
        cv2.imshow('Measurement', out)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    if save_out:
        cv2.imwrite(save_out, out)

    return results

if __name__ == "__main__":
    path = "C:\\QC Detector\\QC-Detector\\input\\temp_assets\\WhatsApp Image 2025-11-11 at 14.54.53.jpeg"
    mm_per_px = None
    res = measure_sandals(path, mm_per_px=mm_per_px, draw_output=True, save_out="output/measured.png")
    print("Hasil:", res)
