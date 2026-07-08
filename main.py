#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
  K1 AI 隐私安全哨兵 - 入口
  从 unified_sentinel.py 第 847-865 行提取

  运行方式:
    sudo python3 main.py
    sudo python3 main.py --no-voice    # 仅键盘控制
    sudo python3 main.py --no-scan     # 仅检测不扫描
=============================================================================
"""

import sys
import os
import signal
import argparse

# 确保项目根目录在 sys.path 中，使 src.xxx 导入正确
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def main():
    parser = argparse.ArgumentParser(description="K1 AI 隐私安全哨兵")
    parser.add_argument("--no-voice", action="store_true", help="禁用语音控制")
    parser.add_argument("--no-scan", action="store_true", help="禁用自动扫描")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, lambda s, f: None)  # 由主循环处理

    from src.core.sentinel import SentinelSystem

    sentinel = SentinelSystem(
        use_voice=not args.no_voice,
        do_scan=not args.no_scan,
    )
    sentinel.run()


if __name__ == "__main__":
    main()
