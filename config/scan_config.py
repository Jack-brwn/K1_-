# -*- coding: utf-8 -*-
import os

# PWM 通道
PAN_CHIP_PATH = '/sys/class/pwm/pwmchip0'
TILT_CHIP_PATH = '/sys/class/pwm/pwmchip1'

# 脉冲范围（纳秒）
PAN_MIN = 500000
PAN_MAX = 2000000
TILT_MIN = 500000
TILT_MAX = 1273000

# 扫描参数（减慢速度，提高图像清晰度）
PAN_STEPS = 35
TILT_STEPS = 8
SCAN_DELAY = 0.10          # 从0.04改为0.10，更慢更稳定

# 拍照参数
CAPTURE_INTERVAL_STEPS = 3
CAMERA_DEVICE = 20

# 报警参数
ALERT_THRESHOLD = 0.6
ALERT_CONSECUTIVE = 3
YOLO_CONF_THRESHOLD = 0.3

# 扩展目标类别（包含笔记本电脑、手机、摄像头等）
CLASS_NAMES = {
    63: '笔记本电脑',
    64: '鼠标',
    65: '遥控器',
    66: '键盘',
    67: '手机',
    72: '电视',
    73: '摄像头',
    74: '平板',
    76: '微波炉',
    77: '烤箱',
}
TARGET_CLASSES = list(CLASS_NAMES.keys())

# 路径
PROJECT_ROOT = '/home/bianbu/Project'
CAPTURE_DIR = os.path.join(PROJECT_ROOT, 'data/captures')
MODEL_DIR = os.path.join(PROJECT_ROOT, 'models')
LIB_DIR = os.path.join(PROJECT_ROOT, 'lib')

os.makedirs(CAPTURE_DIR, exist_ok=True)
os.makedirs(os.path.join(CAPTURE_DIR, 'alerts'), exist_ok=True)
