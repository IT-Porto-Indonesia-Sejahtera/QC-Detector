# yolo_inference

YOLOv8n-seg inference module with hybrid ROI approach and "Safety Net" fallback.

Uses the nano variant (`yolov8n-seg.pt`, ~13 MB) optimized for CPU inference,
with an IoU-based comparison between AI mask and precision-refined mask.

::: model.yolo_inference
    options:
      members:
        - get_model
        - segment_image
        - get_mask_and_contour
