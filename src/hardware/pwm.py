#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
  PWM 舵机控制类 (sysfs)
  从 unified_sentinel.py 第 99-135 行提取
=============================================================================
"""

import os
import time

from src.core.terminal import green, red


class PWM:
    """PWM 舵机控制（Linux sysfs 接口）"""

    @staticmethod
    def _write(path, value):
        try:
            with open(path, 'w') as f:
                f.write(str(value))
            return True
        except Exception:
            return False

    @staticmethod
    def init(chip_path, period_ns=5000000, channel=0):
        """初始化 PWM 通道，返回是否成功"""
        PWM._write(f"{chip_path}/unexport", channel)
        time.sleep(0.05)
        if not PWM._write(f"{chip_path}/export", channel):
            return False
        time.sleep(0.05)
        pwm_dir = f"{chip_path}/pwm{channel}"
        if not os.path.isdir(pwm_dir):
            return False
        PWM._write(f"{pwm_dir}/period", period_ns)
        # 初始化为中间位置避免舵机跳变 (修复问题1)
        mid_duty = 500000  # 安全默认值, 在_center()中会被覆盖
        PWM._write(f"{pwm_dir}/duty_cycle", mid_duty)
        PWM._write(f"{pwm_dir}/enable", 1)
        return True

    @staticmethod
    def set(chip_path, duty_ns, channel=0):
        """设置占空比 (ns)"""
        pwm_dir = f"{chip_path}/pwm{channel}"
        PWM._write(f"{pwm_dir}/duty_cycle", duty_ns)
        PWM._write(f"{pwm_dir}/enable", 1)

    @staticmethod
    def cleanup(chip_path, channel=0):
        """释放 PWM 通道"""
        pwm_dir = f"{chip_path}/pwm{channel}"
        PWM._write(f"{pwm_dir}/enable", 0)
        PWM._write(f"{chip_path}/unexport", channel)
