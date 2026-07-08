#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP32 自动通信模块 — 串口触发扫描 + HTTP轮询数据
替代手动点击ESP32屏幕
"""
import serial
import time
import os
import re
import json
import threading
from datetime import datetime

SERIAL_PORT = '/dev/ttyUSB0'
BAUD = 115200
DATA_DIR = '/home/bianbu/data'
HTTP_HOST = '192.168.4.1'
HTTP_PORT = 80


class ESP32Comm:
    """ESP32 自动通信: 串口命令 + HTTP数据获取"""

    def __init__(self):
        self.ser = None
        self.ok = False
        self._init_serial()

    def _init_serial(self):
        try:
            self.ser = serial.Serial(SERIAL_PORT, BAUD, timeout=3)
            time.sleep(0.5)
            # Flush startup messages
            self.ser.reset_input_buffer()
            self.ok = True
            print(f'  [ESP32] Serial OK: {SERIAL_PORT}')
        except Exception as e:
            print(f'  [ESP32] Serial fail: {e}')
            print(f'  [ESP32] Will use HTTP fallback: {HTTP_HOST}:{HTTP_PORT}')
            self.ok = False

    def send_cmd(self, cmd, timeout=5):
        """Send serial command and return response"""
        if not self.ser or not self.ok:
            return None
        try:
            self.ser.reset_input_buffer()
            self.ser.write((cmd + '\r\n').encode('utf-8'))
            time.sleep(0.3)
            lines = []
            deadline = time.time() + timeout
            while time.time() < deadline:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode('utf-8', errors='replace').strip()
                    if line:
                        lines.append(line)
                else:
                    time.sleep(0.1)
            return '\n'.join(lines)
        except Exception as e:
            print(f'  [ESP32] cmd error: {e}')
            return None

    def trigger_scan(self):
        """Trigger a full scan: WiFi + BLE + Magnetometer"""
        result = {'wifi': [], 'ble': [], 'mag': None, 'timestamp': time.time()}

        # Try serial commands
        if self.ok:
            resp = self.send_cmd('scan')
            if resp:
                result['raw'] = resp
                return self._parse_response(resp, result)

        # HTTP fallback
        try:
            import urllib.request
            # Try common ESP32 API endpoints
            for endpoint in ['/api/scan', '/scan', '/status', '/data']:
                try:
                    url = f'http://{HTTP_HOST}:{HTTP_PORT}{endpoint}'
                    req = urllib.request.urlopen(url, timeout=3)
                    data = req.read().decode('utf-8', errors='replace')
                    if data:
                        result['raw'] = data
                        return self._parse_response(data, result)
                except Exception:
                    continue
        except Exception:
            pass

        return result

    def _parse_response(self, text, result):
        """Parse ESP32 response for WiFi/BLE/Mag data"""
        # WiFi RSSI
        wifi_matches = re.findall(
            r'WiFi.*?(-?\d+)\s*dBm|RSSI[:\s]*(-?\d+)', text, re.IGNORECASE)
        for m in wifi_matches:
            rssi = int(m[0] or m[1])
            result['wifi'].append({'rssi': rssi})

        # BLE devices
        ble_count = len(re.findall(r'\[ble\]|BLE.*device|devs', text, re.IGNORECASE))
        result['ble'] = [{'count': ble_count}] if ble_count > 0 else []

        # Magnetometer
        mag_match = re.search(
            r'Mag anomaly.*?(\d+)|\|B\|[:\s]*(\d+)', text, re.IGNORECASE)
        if mag_match:
            val = int(mag_match.group(1) or mag_match.group(2))
            result['mag'] = val

        return result

    def get_rf_score(self):
        """Get RF risk score (0-1) from ESP32 data"""
        data = self.trigger_scan()
        score = 0.0

        # WiFi: stronger signals = higher risk
        strong_wifi = sum(1 for w in data.get('wifi', [])
                         if w.get('rssi', -99) > -50)
        if strong_wifi >= 3:
            score += 0.3
        elif strong_wifi >= 1:
            score += 0.15

        # BLE: more devices = higher risk
        ble_count = len(data.get('ble', []))
        if ble_count >= 5:
            score += 0.4
        elif ble_count >= 2:
            score += 0.2
        elif ble_count >= 1:
            score += 0.1

        if strong_wifi >= 2 and ble_count >= 2:
            score += 0.2

        return min(score, 1.0), data

    def get_mag_score(self):
        """Get magnetic anomaly score (0-1)"""
        data = self.trigger_scan()
        mag_val = data.get('mag', 0)
        if mag_val is None:
            return 0.05
        # Normalize: 0=normal, 100=extreme anomaly
        return min(mag_val / 100.0, 1.0)

    def save_dump(self):
        """Save current ESP32 data dump to file (for RF analyzer)"""
        data = self.trigger_scan()
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        fname = os.path.join(DATA_DIR, f'serial_{ts}.log')
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(f'===== SYSTEM DATA DUMP =====\n')
            f.write(f'Timestamp: {datetime.now().isoformat()}\n')
            f.write(f'WiFi devices: {data.get("wifi", [])}\n')
            f.write(f'BLE devices: {data.get("ble", [])}\n')
            f.write(f'Mag anomaly: {data.get("mag", "N/A")}\n')
            if data.get('raw'):
                f.write(f'\nRaw:\n{data["raw"]}\n')
            f.write(f'===== END OF DUMP =====\n')
        return fname

    def close(self):
        if self.ser:
            self.ser.close()


# Background dump thread
class ESP32DumpThread:
    """Periodically save ESP32 data dumps"""
    def __init__(self, interval=5):
        self.interval = interval
        self.running = False
        self.esp32 = None
        self.last_rf = 0.1
        self.last_mag = 0.05
        self.lock = threading.Lock()

    def start(self):
        self.running = True
        self.esp32 = ESP32Comm()
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()
        return self

    def _loop(self):
        while self.running:
            try:
                fname = self.esp32.save_dump()
                score, data = self.esp32.get_rf_score()
                mag = self.esp32.get_mag_score()
                with self.lock:
                    self.last_rf = score
                    self.last_mag = mag
                if score > 0.2 or mag > 0.1:
                    print(f'  [ESP32] dump: {os.path.basename(fname)} '
                          f'RF={score:.2f} Mag={mag:.2f}')
            except Exception as e:
                print(f'  [ESP32] dump error: {e}')
            time.sleep(self.interval)

    def get_scores(self):
        with self.lock:
            return self.last_rf, self.last_mag

    def stop(self):
        self.running = False
        if self.esp32:
            self.esp32.close()


if __name__ == '__main__':
    print('ESP32 Communication Test')
    esp = ESP32Comm()
    score, data = esp.get_rf_score()
    print(f'RF Score: {score:.2f}')
    print(f'Mag Score: {esp.get_mag_score():.2f}')
    print(f'Data: {data}')
    fname = esp.save_dump()
    print(f'Saved: {fname}')
    esp.close()
