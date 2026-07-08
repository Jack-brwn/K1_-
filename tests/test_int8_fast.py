#!/usr/bin/env python3
"""Test both INT8 model sizes for performance"""
import time, numpy as np, onnxruntime as ort, spacemit_ort

for name, model_path, shape in [
    ("320x320 INT8", "/home/bianbu/Project/models/yolov8n_int8.onnx", (1,3,320,320)),
    ("192x320 INT8", "/home/bianbu/spacemit-demo/examples/CV/yolov8/model/yolov8n_192x320.q.onnx", (1,3,192,320)),
]:
    try:
        sess = ort.InferenceSession(model_path, providers=["SpaceMITExecutionProvider"])
        iname = sess.get_inputs()[0].name
        img = np.random.randn(*shape).astype(np.float32)

        for _ in range(3):
            sess.run(None, {iname: img})

        times = []
        for _ in range(20):
            t0 = time.perf_counter()
            sess.run(None, {iname: img})
            times.append((time.perf_counter() - t0)*1000)

        avg = sum(times)/len(times)
        print("%s: avg=%.1fms FPS=%.1f" % (name, avg, 1000/avg))
    except Exception as e:
        print("%s: ERROR - %s" % (name, str(e)[:100]))
