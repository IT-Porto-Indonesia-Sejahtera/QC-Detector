# Detection Methods

QC Detector supports four detection methods, each optimized for different scenarios.

## Standard (Contour)

!!! info "Best for: Dark objects with good contrast"

- Traditional OpenCV edge detection
- HSV color filtering for white objects on green background
- Fast and CPU-efficient
- Good for controlled environments

**How it works:**

1. Image preprocessing (color space conversion)
2. Adaptive thresholding and contour detection
3. Mask quality evaluation (smoothness and solidity scoring)
4. Best mask selection from multiple strategies

---

## FastSAM (AI)

!!! info "Best for: Unknown or diverse object types"

- Universal object segmentation using Fast Segment Anything Model
- Good generalization across product types
- Uses `FastSAM-s.pt` (~24 MB model)

**How it works:**

1. Run FastSAM inference at optimal resolution
2. Filter masks by area ratio (reject background and noise)
3. Score candidates by center proximity and area coverage
4. Apply morphological refinement to clean mask edges

---

## YOLO-Seg (AI)

!!! tip "Recommended for most use cases"

- **Hybrid Approach**: AI finds ROI → Traditional CV measures precisely
- Handles all colors equally well (including white-on-green)
- Metrology-grade edge detection with Sobel gradients
- Sub-pixel accuracy with PCA-based endpoints
- Uses `yolov8n-seg.pt` (~13 MB model)

**How it works:**

1. YOLOv8n-seg detects objects → bounding box + mask
2. Extract ROI with 10% margin (prevents edge cutting)
3. Run `strong_mask()` precision refinement inside ROI
4. Compare refined mask with AI mask (IoU check)
5. If IoU > 0.60: use refined mask (sharper edges)
6. If IoU < 0.60: fallback to AI mask (camouflage scenario)
7. PCA-based endpoint detection for final measurement

!!! note "Safety Net"
    The IoU comparison acts as a safety net. When the precision contour diverges
    from the AI mask (e.g., green sandal on green screen), the system automatically
    falls back to the raw YOLO mask instead of producing garbage output.

---

## Advanced (YOLOv8x + SAM)

!!! warning "Requires GPU for best performance"

- **Two-Model Pipeline**: YOLOv8 Extra-Large detects → SAM segments with pixel-perfect precision
- YOLOv8x ("The Spotter"): Extra-Large model sees texture differences invisible to smaller models
- SAM ("The Surgeon"): Segment Anything Model produces studio-quality masks from edge & depth cues
- Uses `yolov8x.pt` (~130 MB) + `sam_b.pt` (~375 MB)

**How it works:**

1. **YOLOv8x Detection** — Finds objects even with low color contrast
2. **Best Object Selection** — Scores candidates by area ratio, center proximity, and confidence
3. **Bounding Box Expansion** — Adds 5% margin for SAM prompt
4. **SAM Segmentation** — Produces pixel-perfect mask from edge & depth cues
5. **Background Filtering** — Rejects masks covering >70% of image (likely background)
6. **Morphological Cleaning** — Removes small noise artifacts
7. **Contour Extraction** — Largest contour becomes the final measurement boundary

!!! note "Fallback Behavior"
    If YOLOv8x finds no objects, the system falls back to a center-point prompt for SAM.
    If both models fail, it gracefully degrades to standard contour detection.

## Performance Comparison

| Method | Speed | Accuracy | Model Size | GPU Required |
|--------|-------|----------|------------|--------------|
| Standard | ⚡⚡⚡ Fast | Good | None | No |
| FastSAM | ⚡⚡ Medium | Very Good | ~24 MB | Optional |
| YOLO-Seg | ⚡⚡ Medium | Excellent ⭐ | ~13 MB | Optional |
| Advanced (YOLOv8x + SAM) | ⚡ Slower | Best ⭐⭐ | ~505 MB | Recommended |
