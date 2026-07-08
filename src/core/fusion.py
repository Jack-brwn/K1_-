#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
  多模态融合评分 + 磁场分析
  融合策略: 视觉35% + 射频35% + 磁场20% + 环境10%
=============================================================================
"""

import random
from config.settings import FUSION_WEIGHTS


def fusion_score(vis, rf, mag=0.1, env=0.1):
    """多模态融合: 视觉 + RF + 磁场 + 环境"""
    w = FUSION_WEIGHTS
    return vis * w["visual"] + rf * w["rf"] + mag * w["mag"] + env * w["env"]


def mag_score(rf_analyzer=None):
    """
    磁场异常分析 — 优先使用ESP32 BMM150实时数据
    返回 0.0(正常) ~ 1.0(异常)
    """
    if rf_analyzer and hasattr(rf_analyzer, 'get_mag_score'):
        try:
            return rf_analyzer.get_mag_score()
        except Exception:
            pass
    try:
        return random.uniform(0.0, 0.2)
    except Exception:
        return 0.05


def env_score():
    """
    环境异常分析 (温度/湿度/光照突变)
    返回 0.0 ~ 1.0
    """
    try:
        # 当前为模拟模式
        return random.uniform(0.0, 0.15)
    except Exception:
        return 0.05


def layered_verify(detected, vis_score, rf_score, mag_s, env_s):
    """
    分层验证: 视觉优先 → RF辅助 → 磁场确认
    返回 (is_threat: bool, total_score: float, source: str)
    source: 'visual' | 'rf' | 'mag' | 'none'
    """
    from config.settings import ALERT_THRESHOLD, RF_ALERT_THRESHOLD, MAG_ALERT_THRESHOLD

    # 第一层: 视觉直接命中 → 报警
    if detected and vis_score >= ALERT_THRESHOLD:
        return True, vis_score, 'visual'

    # 第二层: 视觉弱信号 + RF高 → 报警
    if vis_score > 0.2 and rf_score >= RF_ALERT_THRESHOLD:
        total = fusion_score(vis_score, rf_score, mag_s, env_s)
        if total >= ALERT_THRESHOLD:
            return True, total, 'visual+rf'

    # 第三层: RF独立高 → 磁场确认 → 报警
    if rf_score >= RF_ALERT_THRESHOLD:
        if mag_s >= MAG_ALERT_THRESHOLD:
            total = fusion_score(0.1, rf_score, mag_s, env_s)
            return True, total, 'rf+mag'

    # 全部未触发
    total = fusion_score(vis_score, rf_score, mag_s, env_s)
    return False, total, 'none'
