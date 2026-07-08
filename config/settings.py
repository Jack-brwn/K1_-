# -*- coding: utf-8 -*-
"""K1 AI 隐私安全哨兵 - 集中化配置 (Official YOLOv8n FP32)"""
import os

PROJECT_ROOT    = "/home/bianbu/Project"
MODEL_DIR       = os.path.join(PROJECT_ROOT, "models")
CAPTURE_DIR     = os.path.join(PROJECT_ROOT, "data", "captures")
ALERT_DIR       = os.path.join(CAPTURE_DIR, "alerts")
TMP_DIR         = os.path.join(PROJECT_ROOT, "tmp")
LIB_DIR         = os.path.join(PROJECT_ROOT, "lib")

PAN_CHIP        = "/sys/class/pwm/pwmchip0"
TILT_CHIP       = "/sys/class/pwm/pwmchip1"
PAN_MIN         = 500000
PAN_MAX         = 2000000
TILT_MIN        = 500000
TILT_MAX        = 1273000
PAN_STEPS       = 25
TILT_STEPS      = 8
SCAN_DELAY      = 0.15
CAPTURE_INTERVAL = 1
CAMERA_DEVICE   = 20

# 优先使用FP32标准模型 (80类COCO, 类别映射正确)
# INT8模型备用 (60类+logits输出, 需要sigmoid修正)
MODEL_PATH_INT8  = os.path.join(MODEL_DIR, "yolov8n_int8.onnx")
MODEL_PATH_FP32  = os.path.join(MODEL_DIR, "yolov8n.onnx")
YOLO_CONF        = 0.08
IOU_THRESHOLD    = 0.45
ALERT_THRESHOLD  = 0.10
ALERT_CONSECUTIVE = 1
RF_ALERT_THRESHOLD = 0.5
MAG_ALERT_THRESHOLD = 0.5

# 目标设备类别 (正确COCO映射 — 2026-07-07修正)
# COCO 80类中跟隐私/监控相关的电子设备:
#   62: tv/monitor (电视/显示器)
#   63: laptop (笔记本电脑)
#   64: mouse (鼠标)
#   65: remote (遥控器)
#   66: keyboard (键盘)
#   67: cell phone (手机)
# 注意: COCO中没有"摄像头""平板"类别
#   摄像头可能被识别为 cell phone(67) 或 tv(62)
#   平板可能被识别为 laptop(63) 或 tv(62)
CLASS_NAMES = {
    62: '显示器',
    63: '笔记本电脑',
    65: '摄像头',
    67: '手机',
}
TARGET_CLASSES = list(CLASS_NAMES.keys())

# ASR-LLM-TTS
ASR_LLM_TTS_DIR  = "/home/bianbu/asr-llm-tts/src"
ASR_MODEL_DIR    = "/home/bianbu/asr-llm-tts/src/asr/models"
AUDIO_IN_DEVICE  = "plughw:0,0"
AUDIO_OUT_DEVICE = "plughw:CARD=sndes8326,DEV=0"
RECORD_SR        = 16000

RVV_LIB_PATH     = os.path.join(PROJECT_ROOT, "lib", "libk1_rvv.so")
SPACEMIT_DEMO_PATH = "/home/bianbu/spacemit-demo/examples/CV/yolov8/python"

SERIAL_LOG_DIR  = "/home/bianbu/data"
SAMPLE_RATE = 16000

INFER_THREADS = 4
GRAPH_OPT_LEVEL = "ENABLE_ALL"
MAX_INFER_FPS = 8
CONF_THRESHOLD = 0.25

CPU_CORES_AI    = {4, 5, 6, 7}
CPU_CORES_SCAN  = {0, 1, 2, 3}

FUSION_WEIGHTS = {"visual": 0.35, "rf": 0.35, "mag": 0.20, "env": 0.10}

VAD_ENERGY_THRESHOLD = 100
ASR_CHUNK_SECONDS = 2.5
