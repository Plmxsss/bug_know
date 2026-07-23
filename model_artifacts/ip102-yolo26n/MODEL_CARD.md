# IP102 YOLO26n Model Card

## Identity

- Model name: `ip102-yolo26n`
- Project version: `1.0.0`
- Task: agricultural pest object detection
- Classes: 102
- Input size: 640 pixels
- Weight: `data/runs/yolo26n_bug_know-5/weights/best.pt`
- SHA-256: `643b969aadbad424c2d77f5e819c871488bad70e2836130c4a2a8a0beceeda32`

The weight loaded successfully with Ultralytics 8.4.95. This records the
validation runtime, not a proven original training-library version.

## Intended use

The model is intended for educational and demonstration use in AgriGuard AI.
It locates IP102 agricultural pest classes in uploaded still images. It is not
a plant-disease model, a safety-critical diagnosis system, or an autonomous
pesticide recommendation system.

## Training summary

- Dataset configuration: `data/data.yaml`
- Epochs: 100
- Batch size: 4
- Seed: 42
- Device: CUDA device 0
- Optimizer: automatic selection
- Cosine learning-rate schedule: enabled
- Automatic mixed precision: enabled
- Training was resumed from `last.pt`

The available time column does not establish complete end-to-end training time
because this experiment was resumed.

## Validation metrics

The best recorded validation result occurred at epoch 86:

| Metric | Value |
|---|---:|
| Precision | 0.59071 |
| Recall | 0.61496 |
| mAP50 | 0.62067 |
| mAP50-95 | 0.40732 |

The final epoch mAP50-95 was 0.40098, slightly below the best epoch.

Selected strongest classes by mAP50-95:

| Class ID | Name | mAP50-95 |
|---:|---|---:|
| 90 | 橘二叉蚜 | 0.79600 |
| 95 | 边缘蜡蝉 | 0.76445 |
| 66 | 葡萄天蛾属 | 0.74466 |
| 101 | 叶蝉科 | 0.73162 |
| 65 | 葡萄透翅蛾 | 0.71767 |

Selected weakest classes by mAP50-95:

| Class ID | Name | mAP50-95 |
|---:|---|---:|
| 93 | 瘿蚊属 | 0.00000 |
| 72 | 顶斑小叶蝉 | 0.00000 |
| 54 | 蓟马 | 0.05820 |
| 58 | 刺蛾科 | 0.06349 |
| 17 | 白缘蛾 | 0.09176 |

## Known limitations

- The class distribution is long-tailed, and per-class performance varies
  substantially.
- Small pests and visually similar classes remain difficult.
- The recorded metrics are validation metrics. An independently audited test
  evaluation has not yet been documented.
- The current data split still needs a duplicate and leakage audit.
- Performance on images from different regions, devices, seasons, and lighting
  conditions is not established.
- A detection result is evidence from the vision model, not a confirmed
  agricultural diagnosis.

## Reproducibility artifacts

The manifest records the weight fingerprint, core training settings, metric
artifact paths, and three local smoke-regression images with their SHA-256
fingerprints. Dataset images and binary weights remain outside Git.
