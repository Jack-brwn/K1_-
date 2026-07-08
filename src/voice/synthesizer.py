# -*- coding: utf-8 -*-
"""语音合成 - 预合成WAV播放 + sox音量放大"""
import os, subprocess

RESPONSES_DIR = '/home/bianbu/Project/responses'

# Correct COCO class mapping (2026-07-07 fixed)
ALERT_FILES = {
    62: 'alert_tv',           # 显示器/屏幕 (COCO 62 = tv)
    63: 'alert_laptop',       # 笔记本电脑 (COCO 63 = laptop)
    64: 'alert_mouse',        # 鼠标 (COCO 64 = mouse)
    65: 'alert_remote',       # 遥控器 (COCO 65 = remote)
    66: 'alert_keyboard',     # 键盘 (COCO 66 = keyboard)
    67: 'alert_phone',        # 手机 (COCO 67 = cell phone)
    68: 'alert_microwave',    # 微波炉 (COCO 68 = microwave)
    69: 'alert_oven',         # 烤箱 (COCO 69 = oven)
    72: 'alert_device',       # 冰箱 (COCO 72 = refrigerator)
    73: 'alert_camera',      # 摄像头(红外反光, 非COCO标准类)
    # Fallback for any other target class
}

SYSTEM_KEYS = ['start', 'stop', 'continue', 'photo', 'bye', 'welcome', 'alert_bug']

# sox gain factor (MeloTTS WAV RMS ~-38dB, 需要+20dB = 10x voltage gain)
GAIN = 10


class VoiceSynthesizer:
    last_speak_time = 0  # class-level mute timer
    """预合成WAV播放器"""

    def __init__(self):
        self.ok = os.path.isdir(RESPONSES_DIR)
        if self.ok:
            alert_ok = sum(1 for f in ALERT_FILES.values()
                          if os.path.exists(os.path.join(RESPONSES_DIR, f'{f}.wav')))
            sys_ok = sum(1 for k in SYSTEM_KEYS
                        if os.path.exists(os.path.join(RESPONSES_DIR, f'{k}.wav')))
            total = alert_ok + sys_ok
            expected = len(ALERT_FILES) + len(SYSTEM_KEYS)
            print(f'  [语音] 预合成语音 {total}/{expected} 就绪')
        else:
            print('  [语音] 语音文件目录不存在')

    def _play(self, fname):
        """播放WAV (sox软件放大 -> aplay)"""
        path = os.path.join(RESPONSES_DIR, f'{fname}.wav')
        if not os.path.exists(path):
            return
        try:
            # sox放大音量后管道给aplay
            p1 = subprocess.Popen(
                ['sox', '-v', str(GAIN), path, '-t', 'wav', '-'],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            subprocess.run(
                ['sudo', '-u', 'bianbu', 'aplay', '-q'],
                stdin=p1.stdout, capture_output=True, timeout=10)
            p1.stdout.close()
        except Exception:
            # fallback: direct aplay
            VoiceSynthesizer.last_speak_time = __import__("time").time()
            subprocess.run(['sudo', '-u', 'bianbu', 'aplay', '-q', path],
                capture_output=True, timeout=10)

    def speak_alert(self, class_id):
        fname = ALERT_FILES.get(class_id, 'alert_device')
        self._play(fname)

    def speak_bug(self):
        """播放监听设备告警"""
        self._play('alert_bug')

    def speak(self, key):
        self._play(key)
