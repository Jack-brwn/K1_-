#!/usr/bin/env python3
"""End-to-end test: camera capture + INT8 YOLO inference on K1"""
import sys, os, time, cv2, numpy as np, resource

# Setup same as unified_sentinel
demo_path = "/home/bianbu/spacemit-demo/examples/CV/yolov8/python"
sys.path.insert(0, demo_path)
old_cwd = os.getcwd()
os.chdir(demo_path)
from utils import Yolov8Detection
os.chdir(old_cwd)

CLASS_NAMES = {63:'笔记本',64:'鼠标',65:'遥控器',66:'键盘',67:'手机',
               72:'电视',73:'摄像头',74:'平板',76:'微波炉',77:'烤箱'}
TARGET = list(CLASS_NAMES.keys())

# Load detector
model = '/home/bianbu/Project/models/yolov8n_int8.onnx'
detector = Yolov8Detection(model, conf_threshold=0.3, iou_threshold=0.45)
print("Detector loaded OK")

# Capture
cap = cv2.VideoCapture(20)
ret, frame = cap.read()
cap.release()
print("Frame: %s" % str(frame.shape if ret else "FAIL"))

# Benchmark
times = []
detections = []
for i in range(10):
    inp = detector.preprocess(frame)
    t0 = time.perf_counter()
    outputs = detector.session.run(
        detector.output_names, {detector.input_name: inp})
    boxes, classes, scores = detector.postprocess(outputs)
    elapsed = (time.perf_counter() - t0) * 1000
    times.append(elapsed)
    if boxes is not None and len(boxes) > 0:
        for j in range(len(scores)):
            cls_id = int(classes[j])
            if cls_id in TARGET:
                detections.append((CLASS_NAMES.get(cls_id, str(cls_id)),
                                   float(scores[j])))

avg = sum(times)/len(times)
print("Avg inference: %.1fms (%.1f FPS)" % (avg, 1000/avg))
print("Min: %.1fms  Max: %.1fms" % (min(times), max(times)))

if detections:
    detections.sort(key=lambda x: -x[1])
    print("Detected: %s" % [n for n,s in detections[:5]])
else:
    print("No suspicious devices (normal room)")

mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
print("Memory: %.1f MB" % (mem / 1024))
print("END-TO-END TEST PASSED!")
