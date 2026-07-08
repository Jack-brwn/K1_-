#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI Engine v2.6 - Simple OpenCV+ONNX with bbox support for fine-locking"""
import os, time
import cv2
import numpy as np
import onnxruntime as ort
from config.settings import TARGET_CLASSES as _TARGET_CLASSES

COCO_CLASSES = {
    0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 4: 'airplane',
    5: 'bus', 6: 'train', 7: 'truck', 8: 'boat', 9: 'traffic light',
    10: 'fire hydrant', 11: 'stop sign', 12: 'parking meter', 13: 'bench',
    14: 'bird', 15: 'cat', 16: 'dog', 17: 'horse', 18: 'sheep', 19: 'cow',
    20: 'elephant', 21: 'bear', 22: 'zebra', 23: 'giraffe', 24: 'backpack',
    25: 'umbrella', 26: 'handbag', 27: 'tie', 28: 'suitcase', 29: 'frisbee',
    30: 'skis', 31: 'snowboard', 32: 'sports ball', 33: 'kite',
    34: 'baseball bat', 35: 'baseball glove', 36: 'skateboard',
    37: 'surfboard', 38: 'tennis racket', 39: 'bottle', 40: 'wine glass',
    41: 'cup', 42: 'fork', 43: 'knife', 44: 'spoon', 45: 'bowl',
    46: 'banana', 47: 'apple', 48: 'sandwich', 49: 'orange',
    50: 'broccoli', 51: 'carrot', 52: 'hot dog', 53: 'pizza', 54: 'donut',
    55: 'cake', 56: 'chair', 57: 'couch', 58: 'potted plant', 59: 'bed',
    60: 'dining table', 61: 'toilet', 62: 'tv', 63: 'laptop',
    64: 'mouse', 65: 'remote', 66: 'keyboard', 67: 'cell phone',
    68: 'microwave', 69: 'oven', 70: 'toaster', 71: 'sink',
    72: 'refrigerator', 73: 'book', 74: 'clock', 75: 'vase',
    76: 'scissors', 77: 'teddy bear', 78: 'hair drier', 79: 'toothbrush',
}


class AIEngine:
    def __init__(self):
        self.session = None
        self.inp_h = 320
        self.inp_w = 320
        self.conf = 0.08  # v4.2: balanced
        self.priority_conf = {}
        self._load()
        self.last_time = 0
        self.debug_count = 0

    def _load(self):
        from config.settings import MODEL_PATH_FP32, MODEL_PATH_INT8, YOLO_CONF
        self.conf = YOLO_CONF
        mp = MODEL_PATH_FP32
        if not os.path.exists(mp):
            mp = MODEL_PATH_INT8
        if not os.path.exists(mp):
            print('  [AI] No model found!')
            return
        try:
            opt = ort.SessionOptions()
            opt.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
            opt.intra_op_num_threads = 4
            self.session = ort.InferenceSession(
                mp, opt, providers=['CPUExecutionProvider'])
            inp = self.session.get_inputs()[0]
            self.inp_h, self.inp_w = inp.shape[2], inp.shape[3]
            self.inp_name = inp.name
            print('  [AI] YOLOv8n %dx%d conf=%.2f (%s)' % (
                self.inp_h, self.inp_w, self.conf, os.path.basename(mp)))
        except Exception as e:
            print('  [AI] Load error: %s' % e)

    def _preprocess(self, frame):
        """Simple OpenCV letterbox resize"""
        img_h, img_w = frame.shape[:2]
        r = min(self.inp_h / img_h, self.inp_w / img_w)
        new_h, new_w = int(img_h * r), int(img_w * r)
        resized = cv2.resize(frame, (new_w, new_h))
        pad_h = self.inp_h - new_h
        pad_w = self.inp_w - new_w
        top, left = pad_h // 2, pad_w // 2
        padded = cv2.copyMakeBorder(
            resized, top, pad_h - top, left, pad_w - left,
            cv2.BORDER_CONSTANT, value=(114, 114, 114))
        blob = padded[:, :, ::-1].astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))[np.newaxis, ...]
        return blob, r, top, left, img_h, img_w

    def _decode_and_nms(self, out_data, ratio, pad_top, pad_left, img_h, img_w):
        """Decode YOLO output -> bbox in original image coords + NMS"""
        if len(out_data.shape) == 4:
            _, C, gh, gw = out_data.shape
            out_t = out_data[0].reshape(C, gh * gw).transpose(1, 0)
            # Single scale INT8: simple grid
            fh, fw = gh, gw
            grids_list = []
            strides_list = []
            stride = self.inp_h / fh
            gy, gx = np.meshgrid(np.arange(fh), np.arange(fw), indexing='ij')
            grids_list.append(np.stack([gx.ravel(), gy.ravel()], axis=1))
            strides_list.append(np.full(fh * fw, stride))
            all_grids = np.concatenate(grids_list)
            all_strides = np.concatenate(strides_list)
        else:
            out_t = out_data[0].transpose(1, 0)
            # FP32: 3 feature map scales
            fh1, fw1 = self.inp_h // 8, self.inp_w // 8
            fh2, fw2 = self.inp_h // 16, self.inp_w // 16
            fh3, fw3 = self.inp_h // 32, self.inp_w // 32
            grids_list = []
            strides_list = []
            for fh, fw in [(fh1, fw1), (fh2, fw2), (fh3, fw3)]:
                stride = self.inp_h / fh
                gy, gx = np.meshgrid(np.arange(fh), np.arange(fw), indexing='ij')
                grids_list.append(np.stack([gx.ravel(), gy.ravel()], axis=1))
                strides_list.append(np.full(fh * fw, stride))
            all_grids = np.concatenate(grids_list)
            all_strides = np.concatenate(strides_list)

        N = len(all_grids)
        class_scores = out_t[:N, 4:]
        max_scores = class_scores.max(axis=1)
        max_classes = class_scores.argmax(axis=1)

        mask = max_scores > self.conf
        # Priority: cell phone(67) gets lower threshold (small at 320x320)
        mask = mask | (class_scores[:, 67] > 0.02)
        if mask.sum() == 0:
            return [], [], []

        idx = np.where(mask)[0]
        b = out_t[idx, :4]
        s = max_scores[idx]
        c = max_classes[idx]
        g = all_grids[idx]
        st = all_strides[idx]

        # Decode boxes
        cx = (b[:, 0] * 2 - 0.5 + g[:, 0]) * st
        cy = (b[:, 1] * 2 - 0.5 + g[:, 1]) * st
        bw = ((b[:, 2] * 2) ** 2) * st
        bh = ((b[:, 3] * 2) ** 2) * st

        x1 = (cx - bw / 2 - pad_left) / ratio
        y1 = (cy - bh / 2 - pad_top) / ratio
        x2 = (cx + bw / 2 - pad_left) / ratio
        y2 = (cy + bh / 2 - pad_top) / ratio

        x1 = np.clip(x1, 0, img_w); x2 = np.clip(x2, 0, img_w)
        y1 = np.clip(y1, 0, img_h); y2 = np.clip(y2, 0, img_h)

        # NMS
        areas = (x2 - x1) * (y2 - y1)
        order = s.argsort()[::-1]
        keep = []
        while len(order) > 0:
            i = order[0]
            keep.append(i)
            if len(order) == 1: break
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
            iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
            remaining = order[1:]
            mask = iou < 0.45
            # Person(class 0) overlapping target device: keep device (IOU<0.7)
            if c[i] == 0:
                for jj in range(len(remaining)):
                    if int(c[remaining[jj]]) in _TARGET_CLASSES and iou[jj] < 0.7:
                        mask[jj] = True
            order = remaining[mask]

        # Phone disambiguation: YOLO@320x320 confuses phone(67) as laptop/mouse/remote
        kept_raw_scores = class_scores[idx[keep]]  # (K, 80)
        kept_classes = c[keep].astype(int)
        confuse_map = {63: 'laptop', 64: 'mouse', 65: 'remote'}  # -> phone(67)
        for ki in range(len(keep)):
            cid = kept_classes[ki]
            if cid in confuse_map:
                phone_score = kept_raw_scores[ki, 67]
                cur_score = s[keep[ki]]
                if phone_score > 0.02 and phone_score > cur_score * 0.5:
                    kept_classes[ki] = 67

        result_boxes = np.stack([x1[keep], y1[keep], x2[keep], y2[keep]], axis=1)
        return result_boxes, s[keep], kept_classes

    def infer(self, frame):
        """Return (detected, score, class_id, all_detections)
        Each detection has: class_id, class_name, score, bbox [x1,y1,x2,y2], center (cx,cy)
        """
        if self.session is None:
            return False, 0.0, -1, []

        try:
            blob, r, top, left, img_h, img_w = self._preprocess(frame)
            outputs = self.session.run(None, {self.inp_name: blob})
            boxes, scores, classes = self._decode_and_nms(
                outputs[0], r, top, left, img_h, img_w)

            if len(scores) == 0:
                return False, 0.0, -1, []

            # Build all detections with bbox info
            all_dets = []
            for i in range(len(scores)):
                cid = int(classes[i])
                cname = COCO_CLASSES.get(cid, 'cls_%d' % cid)
                bx = boxes[i]
                all_dets.append({
                    'class_id': cid,
                    'class_name': cname,
                    'score': float(scores[i]),
                    'bbox': [float(bx[0]), float(bx[1]), float(bx[2]), float(bx[3])],
                    'center': (float((bx[0] + bx[2]) / 2), float((bx[1] + bx[3]) / 2)),
                    'area': float((bx[2] - bx[0]) * (bx[3] - bx[1])),
                })

            # Debug logging
            self.debug_count += 1
            if self.debug_count % 20 == 0:
                top = sorted(all_dets, key=lambda d: d['score'], reverse=True)[:5]
                det_str = ', '.join('%s(%.2f)' % (d['class_name'], d['score']) for d in top)
                from config.settings import TARGET_CLASSES
                targets = [d for d in all_dets if d['class_id'] in TARGET_CLASSES]
                t_str = ''
                if targets:
                    t_str = ' || TARGET: ' + ', '.join(
                        '%s@(%.0f,%.0f)' % (d['class_name'], d['center'][0], d['center'][1])
                        for d in targets[:3])
                print('')
                print('  [YOLO] %d detections: %s%s' % (len(all_dets), det_str, t_str))

            # Find best target class
            from config.settings import TARGET_CLASSES
            best_score, best_class, best_det = 0.0, -1, None
            for d in all_dets:
                if d['class_id'] in TARGET_CLASSES and d['score'] > best_score:
                    best_score = d['score']
                    best_class = d['class_id']
                    best_det = d

            if best_score > 0:
                return True, best_score, best_class, all_dets
            return False, 0.0, -1, all_dets

        except Exception as e:
            print('  [AI] infer error: %s' % e)
            return False, 0.0, -1, []

    def get_target_bbox(self, frame):
        """Get best target device bbox for fine-locking.
        Returns (class_name, score, bbox, center) or None."""
        detected, score, class_id, all_dets = self.infer(frame)
        if all_dets:
            from config.settings import TARGET_CLASSES
            targets = [d for d in all_dets if d['class_id'] in TARGET_CLASSES]
            if targets:
                best = max(targets, key=lambda d: d['score'])
                return (best['class_name'], best['score'],
                        best['bbox'], best['center'])
        return None
