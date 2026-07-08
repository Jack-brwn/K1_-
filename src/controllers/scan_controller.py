# -*- coding: utf-8 -*-
import time
import queue
import os
import cv2
from config.scan_config import *
from src.drivers.pwm_hw import pwm_init, pwm_set_duty, pwm_disable, pwm_unexport
from src.drivers.camera_capture import Camera

class ScanController:
    def __init__(self, photo_queue):
        self.photo_queue = photo_queue
        self.running = True
        self.paused = False
        self.cam = Camera(CAMERA_DEVICE)

        print("初始化水平 PWM...")
        if not pwm_init(PAN_CHIP_PATH, 5000000):
            raise RuntimeError("水平 PWM 初始化失败")
        print("初始化垂直 PWM...")
        if not pwm_init(TILT_CHIP_PATH, 5000000):
            raise RuntimeError("垂直 PWM 初始化失败")

        self.tilt_angles = [int(TILT_MIN + (TILT_MAX - TILT_MIN) * i / (TILT_STEPS - 1)) for i in range(TILT_STEPS)]
        self.pan_angles = [int(PAN_MIN + (PAN_MAX - PAN_MIN) * i / (PAN_STEPS - 1)) for i in range(PAN_STEPS)]
        self.step_counter = 0

    def capture_photo(self, pan_duty, tilt_duty):
        if not self.cam.is_opened:
            return
        ret, frame = self.cam.capture(save_path=None, overlay_text=None)
        if ret:
            try:
                self.photo_queue.put_nowait((pan_duty, tilt_duty, frame))
            except queue.Full:
                pass

    def scan(self):
        print("\n开始平滑栅格扫描（垂直来回）")
        print("水平范围：{}~{} ns，垂直范围：{}~{} ns".format(PAN_MIN, PAN_MAX, TILT_MIN, TILT_MAX))
        print("拍照间隔：每 {} 步".format(CAPTURE_INTERVAL_STEPS))
        print("按 Ctrl+C 停止\n")

        try:
            while self.running:
                # 处理暂停：不退出循环，只是等待
                if self.paused:
                    time.sleep(0.1)
                    continue

                # 正向扫描
                for i, tilt_val in enumerate(self.tilt_angles):
                    if not self.running or self.paused:
                        break
                    pwm_set_duty(TILT_CHIP_PATH, tilt_val)
                    if i % 2 == 0:
                        scan_angles = self.pan_angles
                        direction = "→"
                    else:
                        scan_angles = reversed(self.pan_angles)
                        direction = "←"
                    for j, pan_val in enumerate(scan_angles):
                        if not self.running or self.paused:
                            break
                        pwm_set_duty(PAN_CHIP_PATH, pan_val)
                        self.step_counter += 1
                        if self.step_counter % CAPTURE_INTERVAL_STEPS == 0:
                            self.capture_photo(pan_val, tilt_val)
                        print(f"正向 {i+1}/{TILT_STEPS} ({tilt_val}ns)  水平 {j+1}/{PAN_STEPS} {direction}", end='\r')
                        time.sleep(SCAN_DELAY)
                    print()
                    if not self.running or self.paused:
                        break

                if not self.running or self.paused:
                    continue

                # 反向扫描
                for i, tilt_val in enumerate(reversed(self.tilt_angles)):
                    if not self.running or self.paused:
                        break
                    pwm_set_duty(TILT_CHIP_PATH, tilt_val)
                    if i % 2 == 0:
                        scan_angles = self.pan_angles
                        direction = "→"
                    else:
                        scan_angles = reversed(self.pan_angles)
                        direction = "←"
                    for j, pan_val in enumerate(scan_angles):
                        if not self.running or self.paused:
                            break
                        pwm_set_duty(PAN_CHIP_PATH, pan_val)
                        self.step_counter += 1
                        if self.step_counter % CAPTURE_INTERVAL_STEPS == 0:
                            self.capture_photo(pan_val, tilt_val)
                        print(f"反向 {i+1}/{TILT_STEPS} ({tilt_val}ns)  水平 {j+1}/{PAN_STEPS} {direction}", end='\r')
                        time.sleep(SCAN_DELAY)
                    print()
                    if not self.running or self.paused:
                        break

        except KeyboardInterrupt:
            pass
        finally:
            # 只有真正退出时才释放硬件
            if not self.running:
                pwm_disable(PAN_CHIP_PATH)
                pwm_disable(TILT_CHIP_PATH)
                pwm_unexport(PAN_CHIP_PATH)
                pwm_unexport(TILT_CHIP_PATH)
                self.cam.close()
                print("\nPWM 已关闭，摄像头已释放")
            else:
                print("\n扫描暂停，硬件保持开启")

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def stop(self):
        self.running = False
