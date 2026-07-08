# -*- coding: utf-8 -*-
"""
RVV 全加速模块 v3 — libk1_rvv.so 6个函数 (2026-07-06 重新编译)
提供: 预处理(resize+归一化+CHW) / NMS去重 / 高亮检测 / 均匀度 / 滑动滤波 / 传感器融合
"""
import os, ctypes
import numpy as np

RVV_SO = '/home/bianbu/Project/lib/libk1_rvv.so'
_lib = None


def _load():
    global _lib
    if _lib is not None:
        return _lib
    if not os.path.exists(RVV_SO):
        print('  [RVV] libk1_rvv.so not found, using Python fallback')
        return None
    try:
        lib = ctypes.CDLL(RVV_SO)

        # 预处理: 合并 resize+归一化+HWC→CHW
        lib.preprocess_rvv.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),  # src (H×W×3)
            ctypes.c_int, ctypes.c_int,       # src_h, src_w
            ctypes.POINTER(ctypes.c_float),   # dst (3×dst_h×dst_w)
            ctypes.c_int, ctypes.c_int,       # dst_h, dst_w
        ]
        lib.preprocess_rvv.restype = None

        # NMS 去重
        lib.nms_rvv.argtypes = [
            ctypes.POINTER(ctypes.c_float),   # boxes (N×4)
            ctypes.POINTER(ctypes.c_float),   # scores (N)
            ctypes.c_int,                     # n
            ctypes.c_float,                   # iou_thr
            ctypes.POINTER(ctypes.c_int),     # keep (out)
        ]
        lib.nms_rvv.restype = ctypes.c_int

        # 高亮像素计数
        lib.highlight_count_rvv.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),   # data
            ctypes.c_int,                     # total
            ctypes.c_int,                     # thresh
        ]
        lib.highlight_count_rvv.restype = ctypes.c_int

        # 均匀度评分
        lib.uniformity_rvv.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),   # data
            ctypes.c_int,                     # total
        ]
        lib.uniformity_rvv.restype = ctypes.c_float

        # 滑动窗口滤波
        lib.moving_average_rvv.argtypes = [
            ctypes.POINTER(ctypes.c_float),   # data
            ctypes.POINTER(ctypes.c_float),   # filtered
            ctypes.c_int,                     # n
            ctypes.c_int,                     # win_size
        ]
        lib.moving_average_rvv.restype = None

        # 多传感器融合
        lib.sensor_fusion_rvv.argtypes = [
            ctypes.POINTER(ctypes.c_float),   # signals (C×N)
            ctypes.POINTER(ctypes.c_float),   # weights (C)
            ctypes.POINTER(ctypes.c_float),   # fused (N)
            ctypes.c_int,                     # channels
            ctypes.c_int,                     # n
        ]
        lib.sensor_fusion_rvv.restype = None

        _lib = lib
        return lib
    except Exception as e:
        print(f'  [RVV] load error: {e}')
        return None


def preprocess_rvv(frame_bgr, target_h=192, target_w=320):
    """RVV加速预处理: resize+归一化+HWC→CHW, 返回 (1,3,H,W) float32 blob"""
    lib = _load()
    if lib is None:
        # Python fallback
        import cv2
        resized = cv2.resize(frame_bgr, (target_w, target_h))
        blob = resized.astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))
        return np.expand_dims(blob, 0)

    src_h, src_w = frame_bgr.shape[:2]
    src = np.ascontiguousarray(frame_bgr.ravel(), dtype=np.uint8)
    dst = np.empty(3 * target_h * target_w, dtype=np.float32)

    lib.preprocess_rvv(
        src.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
        src_h, src_w,
        dst.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        target_h, target_w)
    return dst.reshape(1, 3, target_h, target_w).copy()


def nms_rvv(boxes, scores, iou_threshold=0.45):
    """RVV加速NMS, 输入boxes(N,4) scores(N), 返回keep索引列表"""
    lib = _load()
    if lib is None or len(boxes) == 0:
        if len(scores) > 0:
            return [int(np.argmax(scores))]
        return []

    n = len(scores)
    boxes_f32 = np.ascontiguousarray(boxes, dtype=np.float32)
    scores_f32 = np.ascontiguousarray(scores, dtype=np.float32)
    keep = np.zeros(n, dtype=np.int32)

    count = lib.nms_rvv(
        boxes_f32.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        scores_f32.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        n, ctypes.c_float(iou_threshold),
        keep.ctypes.data_as(ctypes.POINTER(ctypes.c_int)))
    return keep[:count].tolist()


def highlight_count_rvv(gray_frame, threshold=200):
    """RVV加速高亮像素计数"""
    lib = _load()
    if lib is None:
        return int(np.sum(gray_frame > threshold))
    total = gray_frame.size
    data = np.ascontiguousarray(gray_frame.ravel(), dtype=np.uint8)
    return lib.highlight_count_rvv(
        data.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
        total, threshold)


def uniformity_rvv(gray_frame):
    """RVV加速均匀度评分 (1.0=完全均匀, <0.7=可疑)"""
    lib = _load()
    if lib is None:
        var = np.var(gray_frame)
        return 1.0 - np.clip(var / 10000, 0, 1)
    total = gray_frame.size
    data = np.ascontiguousarray(gray_frame.ravel(), dtype=np.uint8)
    return lib.uniformity_rvv(
        data.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), total)


def moving_average_rvv(signal, win_size=5):
    """RVV加速滑动窗口均值滤波, 返回滤波后信号"""
    lib = _load()
    if lib is None:
        return np.convolve(signal, np.ones(win_size)/win_size, mode='same')
    n = len(signal)
    data = np.ascontiguousarray(signal, dtype=np.float32)
    filt = np.empty(n, dtype=np.float32)
    lib.moving_average_rvv(
        data.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        filt.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        n, win_size)
    return filt


def sensor_fusion_rvv(signals, weights):
    """RVV加速多传感器融合: signals(C×N) × weights(C) → fused(N)"""
    lib = _load()
    if lib is None:
        return np.average(signals, axis=0, weights=weights)
    channels, n = signals.shape
    sig = np.ascontiguousarray(signals.ravel(), dtype=np.float32)
    w = np.ascontiguousarray(weights, dtype=np.float32)
    fused = np.empty(n, dtype=np.float32)
    lib.sensor_fusion_rvv(
        sig.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        w.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        fused.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        channels, n)
    return fused


def rf_stat_rvv(signal):
    """RF信号统计: [mean, std, peak_count] (纯Python实现, C库无此函数)"""
    n = len(signal)
    if n == 0:
        return [0.0, 0.0, 0.0]
    data = np.asarray(signal, dtype=np.float32)
    # RVV加速滤波
    filtered = moving_average_rvv(data, win_size=min(5, n))
    mean = float(np.mean(filtered))
    std = float(np.std(filtered))
    peak_count = int(np.sum(filtered > (mean + std)))
    return [mean, std, peak_count]
