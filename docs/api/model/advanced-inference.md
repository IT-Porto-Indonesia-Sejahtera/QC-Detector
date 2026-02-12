# advanced_inference

Advanced two-model segmentation pipeline using **YOLOv8x + SAM**.

- **The Spotter (YOLOv8x)**: Extra-Large detection model that finds bounding boxes using texture differences
- **The Surgeon (SAM)**: Segment Anything Model that produces pixel-perfect masks from edge & depth cues

::: model.advanced_inference
    options:
      members:
        - get_yolo_model
        - get_sam_model
        - segment_image
        - get_mask_and_contour
