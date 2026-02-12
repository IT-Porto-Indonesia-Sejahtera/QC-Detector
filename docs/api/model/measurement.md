# measurement

Core measurement logic for the QC Detector system — mask generation, contour scoring, endpoint detection, and the main measurement pipeline.

::: model.measurement
    options:
      members:
        - evaluate_mask_quality
        - get_channel_mask
        - strong_mask
        - auto_select_mask
        - endpoints_via_minrect
        - find_largest_contours
        - principal_axis
        - project_onto_axis
        - refined_endpoints
        - measure_sandals
