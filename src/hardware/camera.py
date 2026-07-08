# -*- coding: utf-8 -*-
"""Simple camera - OpenCV only, no v4l2-ctl conflicts"""
import threading, time

class Camera:
    def __init__(self, device_id=20):
        self.device_id = device_id
        self.cap = None
        self.ok = False
        self._ready = threading.Event()
        print('  [Camera] opening...', end='', flush=True)
        t = threading.Thread(target=self._open, daemon=True)
        t.start()

    def _open(self):
        import cv2
        c = cv2.VideoCapture(self.device_id)
        c.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        c.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        c.set(cv2.CAP_PROP_FPS, 30)
        # Discard initial frames for auto-exposure to settle
        for _ in range(15):
            ret, _ = c.read()
            if ret:
                time.sleep(0.05)
        self.cap = c
        self.ok = c.isOpened()
        self._ready.set()

    def wait_ready(self, timeout=8):
        self._ready.wait(timeout=timeout)
        return self.ok

    def grab(self):
        if not self._ready.wait(timeout=8):
            return False, None
        if self.cap is None or not self.ok:
            return False, None
        ret, frame = self.cap.read()
        return ret, frame

    def close(self):
        if self.cap:
            self.cap.release()
