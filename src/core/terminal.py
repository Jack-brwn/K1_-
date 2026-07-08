#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
  终端颜色输出工具
  从 unified_sentinel.py 第 83-94 行提取
=============================================================================
"""

C_GREEN  = '\033[92m'
C_YELLOW = '\033[93m'
C_RED    = '\033[91m'
C_CYAN   = '\033[96m'
C_RESET  = '\033[0m'
C_BOLD   = '\033[1m'


def green(s):
    return f"{C_GREEN}{s}{C_RESET}"


def yellow(s):
    return f"{C_YELLOW}{s}{C_RESET}"


def red(s):
    return f"{C_RED}{s}{C_RESET}"


def cyan(s):
    return f"{C_CYAN}{s}{C_RESET}"


def bold(s):
    return f"{C_BOLD}{s}{C_RESET}"
