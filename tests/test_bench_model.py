#!/home/bianbu/vosk_project/venv/bin/python3
"""K1 YOLO Benchmark - Test different configs"""
import time, numpy as np, onnxruntime as ort, onnx

model = "/home/bianbu/Project/models/yolov8n.onnx"
img = np.random.randn(1, 3, 320, 320).astype(np.float32)

# Analyze model
m = onnx.load(model)
print("Model: %d nodes" % len(m.graph.node))
ops = {}
for n in m.graph.node:
    ops[n.op_type] = ops.get(n.op_type, 0) + 1
for k,v in sorted(ops.items(), key=lambda x:-x[1])[:10]:
    print("  %s: %d" % (k, v))

# Benchmark different thread configs
print("\n--- Benchmark (10 iters each) ---")
for threads in [1, 2, 4]:
    for opt_name in ["ENABLE_BASIC", "ENABLE_EXTENDED", "ENABLE_ALL"]:
        try:
            level = getattr(ort.GraphOptimizationLevel, "ORT_" + opt_name)
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = threads
            opts.inter_op_num_threads = 1
            opts.graph_optimization_level = level
            opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

            sess = ort.InferenceSession(model, opts, providers=['CPUExecutionProvider'])
            iname = sess.get_inputs()[0].name

            # Warmup
            for _ in range(3):
                sess.run(None, {iname: img})

            # Timed
            t0 = time.perf_counter()
            for _ in range(10):
                sess.run(None, {iname: img})
            elapsed = (time.perf_counter() - t0) * 1000 / 10

            print("threads=%d opt=%-18s -> %8.1fms avg" % (threads, opt_name, elapsed))

        except Exception as e:
            print("threads=%d opt=%-18s -> ERROR: %s" % (threads, opt_name, str(e)[:100]))
