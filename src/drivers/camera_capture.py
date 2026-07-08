# -*- coding: utf-8 -*-
"""
摄像头驱动
"""
import cv2
import os

class Camera:
    def __init__(self, device_id=20):
        self.device_id = device_id
        self.cap = None
        self.is_opened = False
        self._open()

    def _open(self):
        self.cap = cv2.VideoCapture(self.device_id)
        if not self.cap.isOpened():
            print(f"[Camera] 打开 /dev/video{self.device_id} 失败")
            return
        self.is_opened = True
        print(f"[Camera] ✅ 摄像头已打开 (设备: /dev/video{self.device_id})")

    def capture(self, save_path=None, overlay_text=None):
        if not self.is_opened or self.cap is None:
            return False, None
        ret, frame = self.cap.read()
        if not ret:
            return False, None
        if overlay_text:
            cv2.putText(frame, overlay_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            cv2.imwrite(save_path, frame)
        return True, frame

    def close(self):
        if self.cap:
            self.cap.release()
            self.is_opened = False
            print("[Camera] 摄像头已关闭")
