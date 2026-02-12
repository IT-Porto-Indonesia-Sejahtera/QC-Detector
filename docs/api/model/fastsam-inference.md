# fastsam_inference

FastSAM (Fast Segment Anything Model) inference module for universal object segmentation.

Uses `FastSAM-s.pt` (~24 MB) — the smaller variant optimized for speed.

::: model.fastsam_inference
    options:
      members:
        - get_model
        - is_available
        - refine_sam_mask
        - segment_image
        - get_mask_and_contour
