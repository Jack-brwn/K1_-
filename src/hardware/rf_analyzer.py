#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RF analyzer - simulated + ESP32 fallback (non-blocking)"""
import os, glob, re, random, time

from src.core.terminal import green, yellow
from config.settings import SERIAL_LOG_DIR


class RFAnalyzer:
    def __init__(self):
        self.data_dir = SERIAL_LOG_DIR
        self.available = os.path.isdir(self.data_dir)
        self._last_score = 0.08
        self._last_mag = 0.04
        self._spike_timer = time.time()
        self._spike_pos = random.randint(30, 60)  # random frame for RF spike

        if self.available:
            log_count = len(glob.glob(f'{self.data_dir}/serial_*.log'))
            print(f'  {green(chr(0x2713))} RF数据目录 ({log_count} logs)')
        else:
            print(f'  {yellow(chr(0x26A0))} RF模拟模式')

    def _get_latest_dump(self):
        files = sorted(
            glob.glob(f'{self.data_dir}/serial_*.log'),
            key=os.path.getmtime, reverse=True)
        if not files:
            return None
        try:
            with open(files[0], 'r', errors='ignore') as f:
                content = f.read()
            start = content.rfind('===== SYSTEM DATA DUMP =====')
            if start == -1: return None
            end = content.find('===== END OF DUMP =====', start)
            return content[start:end] if end > 0 else content[start:]
        except Exception:
            return None

    def get_score(self):
        """RF score 0-1. Simulated with periodic spikes to test bug detection."""
        # Try real ESP32 data first
        if self.available:
            try:
                dump = self._get_latest_dump()
                if dump:
                    wifi_rssis = [int(m.group(1)) for m in
                                  re.finditer(r'(-?\d+)\s*dBm', dump)]
                    ble_count = len(re.findall(r'\[\s*\d+\]', dump))
                    strong = sum(1 for r in wifi_rssis if r > -50)
                    score = 0.0
                    if strong >= 3: score += 0.3
                    elif strong >= 1: score += 0.15
                    if ble_count >= 5: score += 0.4
                    elif ble_count >= 2: score += 0.2
                    if strong >= 2 and ble_count >= 2: score += 0.2
                    if score > 0.01:
                        self._last_score = min(score, 1.0)
                        return self._last_score
            except Exception:
                pass

        # Simulated RF with periodic spikes
        base = 0.03 + random.uniform(0, 0.08)
        # Every ~50 frames, create an RF hotspot to test bug detection
        self._spike_pos -= 1
        if self._spike_pos <= 0:
            base = 0.25 + random.uniform(0, 0.25)  # spike!
            self._spike_pos = random.randint(40, 80)  # reset timer
        elif time.time() - self._spike_timer > 15:
            # Occasional moderate spike
            base = 0.12 + random.uniform(0, 0.10)
            self._spike_timer = time.time()

        self._last_score = base
        return base

    def get_mag_score(self):
        """Magnetic anomaly 0-1."""
        if self.available:
            try:
                dump = self._get_latest_dump()
                if dump:
                    mag_match = re.search(
                        r'Mag anomaly.*?(\d+)|B[:\s]*(\d+)', dump, re.IGNORECASE)
                    if mag_match:
                        val = int(mag_match.group(1) or mag_match.group(2))
                        self._last_mag = min(val / 100.0, 1.0)
                        return self._last_mag
            except Exception:
                pass

        # Simulated: low baseline, occasional spike
        base = random.uniform(0.01, 0.06)
        if random.random() < 0.03:  # 3% chance of spike
            base = 0.12 + random.uniform(0, 0.15)
        self._last_mag = base
        return base

    def stop(self):
        pass
