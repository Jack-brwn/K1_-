# -*- coding: utf-8 -*-
import os
import glob
import re

class RFAnalyzer:
    def __init__(self, data_dir='/home/bianbu/data'):
        self.data_dir = data_dir

    def get_latest_file(self):
        files = glob.glob(os.path.join(self.data_dir, 'serial_*.log'))
        if not files:
            print("⚠️ 未找到 serial_*.log 文件")
            return None
        files.sort(key=lambda f: os.path.basename(f))
        latest = files[-1]
        print(f"📂 最新日志文件: {latest}")
        return latest

    def read_log_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            return ""

    def parse_latest_dump(self, content):
        wifi_rssis = []
        ble_count = 0
        in_wifi = False
        in_ble = False

        # 找最新一次 DUMP
        start_marker = "===== SYSTEM DATA DUMP ====="
        end_marker = "===== END OF DUMP ====="
        last_start = content.rfind(start_marker)
        if last_start == -1:
            print("⚠️ 未找到 SYSTEM DATA DUMP 段")
            return [], 0
        last_end = content.find(end_marker, last_start)
        if last_end == -1:
            last_end = len(content)
        dump = content[last_start:last_end]
        print(f"📄 提取 DUMP 长度: {len(dump)} 字符")

        for line in dump.splitlines():
            if '--- WiFi Scan Results ---' in line:
                in_wifi = True
                in_ble = False
                continue
            if '--- BLE Scan Results ---' in line:
                in_wifi = False
                in_ble = True
                continue
            if '--- Magnetometer ---' in line or '--- Storage ---' in line:
                in_wifi = False
                in_ble = False

            if in_wifi:
                rssi_match = re.search(r'(-?\d+)\s*dBm', line)
                if rssi_match:
                    wifi_rssis.append(int(rssi_match.group(1)))

            if in_ble:
                if re.search(r'\[\s*\d+\]', line):
                    ble_count += 1

        print(f"📊 解析结果: WiFi信号 {len(wifi_rssis)} 个, BLE设备 {ble_count} 个")
        return wifi_rssis, ble_count

    def calculate_rf_score(self, wifi_rssis, ble_count):
        score = 0.0
        strong_wifi = sum(1 for rssi in wifi_rssis if rssi > -50)
        if strong_wifi >= 3:
            score += 0.3
        elif strong_wifi >= 1:
            score += 0.15
        if ble_count >= 5:
            score += 0.4
        elif ble_count >= 2:
            score += 0.2
        elif ble_count >= 1:
            score += 0.1
        if strong_wifi >= 2 and ble_count >= 2:
            score += 0.2
        return min(score, 1.0)

    def get_rf_score(self):
        file_path = self.get_latest_file()
        if not file_path:
            return 0.0
        content = self.read_log_file(file_path)
        if not content:
            return 0.0
        wifi_rssis, ble_count = self.parse_latest_dump(content)
        if not wifi_rssis and ble_count == 0:
            return 0.0
        score = self.calculate_rf_score(wifi_rssis, ble_count)
        print(f"📡 射频评分: {score:.3f}")
        return score
