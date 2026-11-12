"""Датасет құрастырғыштың таза функцияларын тексеру."""
from PIL import Image

from ml.prepare_data import crop_box, is_green, iou, sample_background


def test_crop_box_adds_margin_and_clamps():
    # 10..30 бокс, 25% жиек → 5..35; бірақ сурет шетінен шықпауы керек
    box = crop_box(img_w=100, img_h=100, bbox=[10, 10, 20, 20], margin=0.25, min_side=0)
    assert box == (5, 5, 35, 35)
    edge = crop_box(img_w=100, img_h=100, bbox=[0, 0, 20, 20], margin=0.25, min_side=0)
    assert edge[0] == 0 and edge[1] == 0


def test_crop_box_enforces_min_side():
    x0, y0, x1, y1 = crop_box(img_w=500, img_h=500, bbox=[100, 100, 10, 10], margin=0.25, min_side=64)
    assert x1 - x0 >= 64 and y1 - y0 >= 64


def test_iou():
    assert iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0
    assert iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1


def test_sample_background_never_overlaps_boxes():
    boxes = [(0, 0, 300, 300)]
    for seed in range(20):
        bg = sample_background(boxes, img_w=600, img_h=600, side=150, seed=seed)
        assert bg is not None
        assert iou(bg, boxes[0]) == 0


def test_sample_background_returns_none_when_no_room():
    assert sample_background([(0, 0, 100, 100)], img_w=100, img_h=100, side=50, seed=0) is None


def test_is_green():
    assert is_green(Image.new("RGB", (8, 8), (40, 120, 30)))
    assert not is_green(Image.new("RGB", (8, 8), (150, 110, 60)))
