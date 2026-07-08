#!/usr/bin/env python3
"""Test SpaceMIT INT8 model inference performance"""
import time
import numpy as np
import onnxruntime as ort

# Import spacemit_ort to register SpaceMIT provider
import spacemit_ort

# Check providers after import
print("Available providers:", ort.get_available_providers())

model = "/home/bianbu/Project/models/yolov8n_int8.onnx"

# Try with SpaceMIT provider
try:
    sess = ort.InferenceSession(model, providers=["SpaceMITExecutionProvider"])
    print("SUCCESS: SpaceMITExecutionProvider!")
except Exception as e:
    print("SpaceMIT failed:", str(e)[:200])
    print("Trying CPUExecutionProvider...")
    sess = ort.InferenceSession(model, providers=["CPUExecutionProvider"])
    print("CPUExecutionProvider loaded")

iname = sess.get_inputs()[0].name
print("Input:", iname, sess.get_inputs()[0].shape)

img = np.random.randn(1, 3, 320, 320).astype(np.float32)

# Warmup
for _ in range(3):
    sess.run(None, {iname: img})

# Benchmark
times = []
for _ in range(20):
    t0 = time.perf_counter()
    sess.run(None, {iname: img})
    times.append((time.perf_counter() - t0) * 1000)

avg = sum(times) / len(times)
p50 = sorted(times)[len(times)//2]
print("Results (20 iters):")
print("  Avg: %.1f ms" % avg)
print("  P50: %.1f ms" % p50)
print("  FPS: %.1f" % (1000/avg))
print("  Model size: 1.9MB (INT8 quantized)")
