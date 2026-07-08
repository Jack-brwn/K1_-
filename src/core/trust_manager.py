# -*- coding: utf-8 -*-
"""
可信设备管理器
- 记录设备的RF频段/磁场特征
- 匹配已信任设备 → 跳过报警
- 新设备 → 询问是否加入可信名单
"""
import os, json, time

TRUST_FILE = '/home/bianbu/Project/data/trusted.json'


class TrustManager:
    def __init__(self):
        self.trusted = self._load()

    def _load(self):
        if os.path.exists(TRUST_FILE):
            try:
                with open(TRUST_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return []

    def _save(self):
        os.makedirs(os.path.dirname(TRUST_FILE), exist_ok=True)
        with open(TRUST_FILE, 'w') as f:
            json.dump(self.trusted, f, ensure_ascii=False, indent=2)

    def match(self, class_id, rf_score, mag_score):
        """
        匹配已信任设备。返回 (is_trusted, device_name)
        匹配条件: class_id相同 + RF特征接近 + 磁场特征接近
        """
        for dev in self.trusted:
            if dev['class_id'] == class_id:
                rf_match = abs(dev.get('rf_score', 0) - rf_score) < 0.25
                mag_match = abs(dev.get('mag_score', 0) - mag_score) < 0.25
                if rf_match and mag_match:
                    return True, dev.get('name', '未知')
        return False, None

    def add(self, class_id, class_name, rf_score, mag_score):
        """添加设备到可信名单"""
        device = {
            'class_id': class_id,
            'name': class_name,
            'rf_score': round(rf_score, 3),
            'mag_score': round(mag_score, 3),
            'added_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        self.trusted.append(device)
        self._save()
        return len(self.trusted)

    def remove(self, class_id, rf_score, mag_score):
        """移除可信设备"""
        self.trusted = [d for d in self.trusted
                        if not (d['class_id'] == class_id and
                                abs(d['rf_score'] - rf_score) < 0.25 and
                                abs(d['mag_score'] - mag_score) < 0.25)]
        self._save()

    def list_all(self):
        return self.trusted
