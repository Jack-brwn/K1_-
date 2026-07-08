# -*- coding: utf-8 -*-
"""三级验证 - 使用 RVV 全加速 (降低误报)"""
import cv2, numpy as np
from src.rvv.rvv_accel import highlight_count_rvv, uniformity_rvv

class ThreeLevelVerify:
    def __init__(self):
        self.lib_ok = True
        print('  [视觉] RVV加速验证就绪')

    def check(self, frame):
        """
        三级验证: 高亮+均匀度
        返回 (is_suspicious: bool, score: float)
        阈值提高以减少误报
        """
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            total = gray.size

            cnt = highlight_count_rvv(gray, 200)
            highlight = cnt / total
            uni = uniformity_rvv(gray)

            score = 0.0
            # 提高阈值，减少日常光照的误报
            if highlight > 0.15:    # 原来0.08
                score += 0.3        # 原来0.4
            if uni < 0.3:           # 原来0.5
                score += 0.4        # 原来0.6
            return score > 0.5, score
        except:
            return False, 0.0
