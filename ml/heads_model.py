"""Масақ детекторының архитектурасы: torchvision Faster R-CNN + MobileNetV3-Large FPN.

Лицензия: torchvision коды BSD-3, COCO салмақтары — torchvision. YOLOv8 (AGPL-3.0)
әдейі қолданылмайды (docs/spec.md). Анкерлер кішірейтілген (16 px-тен), себебі
дрон биіктігінде масақ кадрда кішкентай.
"""
from __future__ import annotations

from torchvision.models.detection import fasterrcnn_mobilenet_v3_large_fpn
from torchvision.models.detection.anchor_utils import AnchorGenerator
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

SIZE = 1024


def build(pretrained: bool = True):
    m = fasterrcnn_mobilenet_v3_large_fpn(
        weights="DEFAULT" if pretrained else None, weights_backbone=None,
        min_size=SIZE, max_size=SIZE, box_detections_per_img=300,
        rpn_pre_nms_top_n_test=2000, rpn_post_nms_top_n_test=1000,
        box_score_thresh=0.05,
    )
    sizes = ((16, 32, 64, 128, 256),) * 3
    m.rpn.anchor_generator = AnchorGenerator(sizes, ((0.5, 1.0, 2.0),) * 3)
    m.roi_heads.box_predictor = FastRCNNPredictor(m.roi_heads.box_predictor.cls_score.in_features, 2)
    return m
