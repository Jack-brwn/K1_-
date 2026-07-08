#!/usr/bin/env python3
"""Test Spacemit INT8 YOLO detector with real camera"""
import sys, os
os.chdir('/home/bianbu/spacemit-demo/examples/CV/yolov8/python')
sys.path.insert(0, '.')

import cv2, numpy as np, time
from utils import Yolov8Detection

# Detector with INT8 model
model = '/home/bianbu/Project/models/yolov8n_int8.onnx'
detector = Yolov8Detection(model, conf_threshold=0.3, iou_threshold=0.45)

# Capture photo
cap = cv2.VideoCapture(20)
ret, frame = cap.read()
cap.release()

if not ret:
    print("ERROR: capture failed")
    exit(1)

print("Photo: %s" % str(frame.shape))

# Warmup
for _ in range(3):
    detector.infer(frame)

# Benchmark
times = []
for _ in range(20):
    t0 = time.perf_counter()
    detector.infer(frame)
    times.append((time.perf_counter()-t0)*1000)

avg = sum(times)/len(times)
p50 = sorted(times)[len(times)//2]
print("INT8 192x320 benchmark (20 runs):")
print("  Avg: %.1fms" % avg)
print("  P50: %.1fms" % p50)
print("  FPS: %.1f" % (1000/avg))

# Result image
result = detector.infer(frame)
os.makedirs('/tmp/test', exist_ok=True)
cv2.imwrite('/tmp/test/result_int8.jpg', result)
print("Result saved: /tmp/test/result_int8.jpg (%d bytes)" % os.path.getsize('/tmp/test/result_int8.jpg'))
print("TEST PASSED!")
