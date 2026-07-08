#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K1 AI v4.0 - 单帧直接报警 + bbox标注 + 射频追踪 + 拍照位锁定
"""
import sys, os, time, select, threading, queue, hashlib
from datetime import datetime

from src.core.terminal import green, yellow, red, cyan, bold
from src.core.fusion import fusion_score, mag_score, env_score, layered_verify
from src.core.trust_manager import TrustManager
from src.ai.ai_engine import AIEngine, COCO_CLASSES
from src.rvv.verification import ThreeLevelVerify
from src.hardware.pwm import PWM
from src.hardware.camera import Camera
from src.hardware.rf_analyzer import RFAnalyzer
from src.voice.recognizer import VoiceRecognizer
from src.voice.synthesizer import VoiceSynthesizer
from config.settings import (
    PAN_CHIP, TILT_CHIP, PAN_MIN, PAN_MAX, TILT_MIN, TILT_MAX,
    PAN_STEPS, TILT_STEPS, SCAN_DELAY, CAPTURE_INTERVAL,
    ALERT_THRESHOLD, CAPTURE_DIR, ALERT_DIR, TMP_DIR,
    CLASS_NAMES, TARGET_CLASSES, CPU_CORES_AI, CPU_CORES_SCAN,
)

FRAME_CX, FRAME_CY = 320, 240


def annotate_frame(frame, detections):
    import cv2
    vis = frame.copy()
    cv2.line(vis, (FRAME_CX-30, FRAME_CY), (FRAME_CX+30, FRAME_CY), (255,0,0), 1)
    cv2.line(vis, (FRAME_CX, FRAME_CY-30), (FRAME_CX, FRAME_CY+30), (255,0,0), 1)
    cv2.circle(vis, (FRAME_CX, FRAME_CY), 40, (255,0,0), 1)
    for d in detections[:8]:
        if 'bbox' not in d or d['bbox'] is None: continue
        x1,y1,x2,y2 = [int(v) for v in d['bbox']]
        is_target = d['class_id'] in TARGET_CLASSES
        color = (0,255,0) if is_target else (160,160,160)
        cv2.rectangle(vis, (x1,y1), (x2,y2), color, 2 if is_target else 1)
        cv2.putText(vis, '%s %.2f' % (d['class_name'][:15], d['score']),
                    (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)
        cv2.circle(vis, (int((x1+x2)/2), int((y1+y2)/2)), 3, color, -1)
    return vis


class SentinelSystem:

    def __init__(self, use_voice=True, do_scan=True):
        print(f"\n{bold('='*58)}")
        print(f"{bold('  K1 AI v4.0 - 单帧报警+射频追踪')}")
        print(f"{bold('='*58)}")
        print(f"  语音: {green('实时ASR') if use_voice else yellow('键盘')}")
        print(f"  报警: {red('单帧直接')} | 锁定: {green('拍照位')}")
        print()

        print(f"{bold('初始化:')}")
        print("  [AI] ", end='', flush=True); self.ai = AIEngine()
        print("  [视觉] ", end='', flush=True); self.verifier = ThreeLevelVerify()
        print("  [射频] ", end='', flush=True); self.rf = RFAnalyzer()
        print("  [语音] ", end='', flush=True)
        self.voice = VoiceRecognizer() if use_voice else None
        self.tts = VoiceSynthesizer()
        print("  [摄像头] ", end='', flush=True); self.cam = Camera(); print()
        print("  [云台] ", end='', flush=True)
        self.pan_ok = PWM.init(PAN_CHIP); self.tilt_ok = PWM.init(TILT_CHIP)
        if self.pan_ok and self.tilt_ok: self._center()
        print(f"  {green(chr(0x2713))} 云台" if self.pan_ok and self.tilt_ok
              else f"  {yellow(chr(0x26A0))} PWM失败")

        print("  [可信] ", end='', flush=True)
        import shutil
        tf = "/home/bianbu/Project/data/trusted.json"
        if os.path.exists(tf):
            try: os.remove(tf)
            except: pass
        for dd in [CAPTURE_DIR, ALERT_DIR]:
            try: shutil.rmtree(dd, ignore_errors=True)
            except: pass
        self.trust = TrustManager()
        print(f"  {green(chr(0x2713))} {len(self.trust.trusted)}个")

        self.running = True; self.paused = True
        self.do_scan = do_scan and self.pan_ok and self.tilt_ok
        self.use_voice = use_voice and self.voice is not None
        self.alarm_active = False
        self.alarm_lock = threading.Lock()
        self.photo_queue = queue.Queue(maxsize=15)
        self.stats = {"frames": 0, "alerts": 0, "trusted_hits": 0,
                       "photos_saved": 0, "start_time": time.time()}
        self._last_frame_hash = None
        self._resume_warmup = 0
        self.current_pan_ns = (PAN_MIN + PAN_MAX) // 2
        self.current_tilt_ns = (TILT_MIN + TILT_MAX) // 2

        # RF tracking for bug detection
        self._rf_history = []
        self._bug_alerted = False
        self.RF_BUG_THRESHOLD = 0.15
        self.MAG_BUG_THRESHOLD = 0.05
        self.BUG_CONSECUTIVE = 2

        for d in [CAPTURE_DIR, ALERT_DIR, TMP_DIR]: os.makedirs(d, exist_ok=True)

        print(f"\n{bold('系统就绪!')} {datetime.now().strftime('%H:%M:%S')}")
        self.tts.speak('welcome')
        print(f"  {yellow('指令:')} {green('启动扫描')}/{green('停止')}/{green('拍照')}/{green('退出')}")
        print(f"{'='*58}\n")

    def _set_pan(self, d):
        self.current_pan_ns = max(PAN_MIN, min(PAN_MAX, d))
        PWM.set(PAN_CHIP, self.current_pan_ns)
    def _set_tilt(self, d):
        self.current_tilt_ns = max(TILT_MIN, min(TILT_MAX, d))
        PWM.set(TILT_CHIP, self.current_tilt_ns)
    def _center(self):
        self._set_pan((PAN_MIN + PAN_MAX) // 2)
        self._set_tilt((TILT_MIN + TILT_MAX) // 2)
    def _move_to(self, pan_ns, tilt_ns):
        self._set_pan(pan_ns)
        self._set_tilt(tilt_ns)
        time.sleep(0.15)

    # ===== 扫描 =====
    def _scan_worker(self):
        try: os.sched_setaffinity(0, CPU_CORES_SCAN)
        except: pass
        ta = [int(TILT_MIN + (TILT_MAX - TILT_MIN) * i / (TILT_STEPS - 1))
              for i in range(TILT_STEPS)]
        pa = [int(PAN_MIN + (PAN_MAX - PAN_MIN) * i / (PAN_STEPS - 1))
              for i in range(PAN_STEPS)]
        self._set_pan(pa[0]); self._set_tilt(ta[0])
        time.sleep(0.3)
        step = 0; settle = SCAN_DELAY

        while self.running:
            for i, tilt in enumerate(ta):
                if not self.running: break
                # Pause in-place: wait here, don't restart from row 1
                while self.paused or self.alarm_active:
                    if not self.running: break
                    time.sleep(0.1)
                if not self.running: break
                self._set_tilt(tilt)
                time.sleep(settle * 0.5)
                scan = pa if i % 2 == 0 else list(reversed(pa))
                direction = "R" if i % 2 == 0 else "L"

                for pan in scan:
                    if not self.running: break
                    while self.paused or self.alarm_active:
                        if not self.running: break
                        time.sleep(0.1)
                    if not self.running: break
                    self._set_pan(pan)
                    step += 1
                    time.sleep(settle)

                    ret, frame = self.cam.grab()
                    if ret and frame is not None:
                        try:
                            self.photo_queue.put_nowait((pan, tilt, frame, time.time()))
                        except queue.Full:
                            pass

                    if step % 10 == 0:
                        h = int((pan - PAN_MIN) / (PAN_MAX - PAN_MIN) * 180)
                        v = int((tilt - TILT_MIN) / (TILT_MAX - TILT_MIN) * 85)
                        print(f"\r  Scan: row{i+1}/{TILT_STEPS} {direction} "
                              f"H={h} V={v} step={step}   ", end='', flush=True)
        print()

    # ===== AI推理 =====
    def _ai_worker(self):
        try: os.sched_setaffinity(0, CPU_CORES_AI)
        except: pass

        while self.running:
            try: photo_pan, photo_tilt, frame, cap_ts = self.photo_queue.get(timeout=0.5)
            except queue.Empty: continue

            while True:
                try: photo_pan, photo_tilt, frame, cap_ts = self.photo_queue.get_nowait()
                except: break

            if frame is None: continue
            frame_hash = hashlib.md5(frame.tobytes()).hexdigest()
            if frame_hash == self._last_frame_hash: continue
            self._last_frame_hash = frame_hash

            if self._resume_warmup > 0:
                self._resume_warmup -= 1; continue

            self.stats["frames"] += 1
            h_deg = int((photo_pan - PAN_MIN) / (PAN_MAX - PAN_MIN) * 180)
            v_deg = int((photo_tilt - TILT_MIN) / (TILT_MAX - TILT_MIN) * 85)

            # YOLO detection
            detected, vis_score, class_id, all_dets = self.ai.infer(frame)
            suspicious, verif_score = self.verifier.check(frame)

            yolo_has = len(all_dets) > 0
            if detected:
                visual_score = vis_score
                if class_id == 67:
                    visual_score = min(vis_score * 2.0, 1.0)
                elif class_id == 63:
                    visual_score = min(vis_score * 1.5, 1.0)
            elif yolo_has:
                visual_score = max(d['score'] for d in all_dets) * 0.8
            else:
                visual_score = verif_score * 0.5 if suspicious else 0.0

            rf_score = self.rf.get_score()
            mag_s = mag_score(self.rf); env_s = env_score()

            # Only target devices trigger threat (not person/chair/etc)
            is_threat, total, source = layered_verify(
                detected, visual_score, rf_score, mag_s, env_s)
            # RF boost: elevated RF alone can trigger at lower visual threshold
            if not is_threat and rf_score > 0.25:
                total2 = fusion_score(visual_score, rf_score, mag_s, env_s)
                if total2 >= 0.18:
                    is_threat, total, source = True, total2, "rf_boost"

            # Class name
            if class_id in CLASS_NAMES:
                class_name = CLASS_NAMES[class_id]
            elif all_dets:
                best = max(all_dets, key=lambda d: d['score'])
                class_name = best['class_name']
                if best['class_id'] in CLASS_NAMES:
                    class_name = CLASS_NAMES[best['class_id']]
            else:
                class_name = '-'

            # Camera IR detection
            if class_id == 65 and suspicious and verif_score > 0.4:
                class_name = '摄像头(红外)'
                detected = True

            # Trusted check
            is_trusted = False
            if class_id in TARGET_CLASSES:
                is_trusted, trusted_name = self.trust.match(class_id, rf_score, mag_s)

            # Target bbox for display
            target_dets = [d for d in all_dets if d['class_id'] in TARGET_CLASSES]
            best_t = max(target_dets, key=lambda d: d['score']) if target_dets else None

            # Annotate + save every detection frame
            if yolo_has:
                import cv2
                annot = annotate_frame(frame, all_dets)
                safe = class_name.replace('/', '_').replace(' ', '_')
                cv2.imwrite(
                    f"{CAPTURE_DIR}/det_{safe}_H{h_deg}_V{v_deg}_{int(time.time()*1000)}.jpg",
                    annot)
                self.stats["photos_saved"] += 1

            # Status line
            extra = ''
            if best_t and 'center' in best_t:
                extra = f" @({best_t['center'][0]:.0f},{best_t['center'][1]:.0f})"
            risk = red("威胁") if is_threat else (yellow("可疑") if total > 0.3 else green("安全"))
            print(f"\r  [{self.stats['frames']}] H{h_deg} V{v_deg} "
                  f"| 视觉={visual_score:.2f} RF={rf_score:.2f} "
                  f"| {risk} | {class_name}{extra}"
                  f"{green(' [可信]') if is_trusted else ''}")

            # === RF tracking for bug detection ===
            self._rf_history.append({
                'h': h_deg, 'v': v_deg, 'pan': photo_pan, 'tilt': photo_tilt,
                'rf': rf_score, 'mag': mag_s, 'ts': time.time()
            })
            if len(self._rf_history) > 60:
                self._rf_history = self._rf_history[-60:]

            # Bug detection: sustained high RF + magnetic anomaly
            if (not self.alarm_active and not self._bug_alerted
                    and len(self._rf_history) >= self.BUG_CONSECUTIVE):
                recent = self._rf_history[-self.BUG_CONSECUTIVE:]
                high_rf = [r for r in recent if r['rf'] >= self.RF_BUG_THRESHOLD]
                high_mag = [r for r in recent if r.get('mag', 0) >= self.MAG_BUG_THRESHOLD]
                if len(high_rf) >= self.BUG_CONSECUTIVE and len(high_mag) >= self.BUG_CONSECUTIVE:
                    with self.alarm_lock: self.alarm_active = True
                    self.stats['alerts'] += 1
                    self._bug_alerted = True
                    peak = max(self._rf_history[-20:], key=lambda r: r['rf'])
                    print(f"\n  {red('🐛 疑似监听设备!')}")
                    print(f"  {yellow('  RF峰值: %.2f  磁场: %.2f')}" % (peak['rf'], peak['mag']))
                    print(f"  {cyan('  锁定: H=%d V=%d')}" % (peak['h'], peak['v']))
                    self._move_to(peak['pan'], peak['tilt'])
                    import cv2
                    ts = int(time.time() * 1000)
                    bug_dir = os.path.join(ALERT_DIR, f'bug_{ts}')
                    os.makedirs(bug_dir, exist_ok=True)
                    for bi in range(10):
                        for _ in range(2): self.cam.grab()
                        ret, bf = self.cam.grab()
                        if ret and bf is not None:
                            cv2.imwrite(f'{bug_dir}/frame_{bi:03d}.jpg', annotate_frame(bf, []))
                        time.sleep(0.03)
                    print(f"  {red('🚨 报警!')} 疑似监听设备")
                    print(f"  🎬 {bug_dir}/")
                    self.tts.speak_bug()
                    print(f"  {cyan('t=信任 c=继续 q=退出')}")
                    self._wait_user_response('监听设备', None, peak['rf'], peak['mag'])

            # === SINGLE-FRAME DIRECT ALERT ===
            if (detected and is_threat and not self.alarm_active
                    and class_id in TARGET_CLASSES and not is_trusted):

                with self.alarm_lock: self.alarm_active = True
                self.stats["alerts"] += 1

                # Move servo BACK to photo position
                print(f"\n  {cyan('>>> 舵机回到拍照位:')} H={h_deg} V={v_deg}")
                self._move_to(photo_pan, photo_tilt)

                import cv2
                ts = int(time.time() * 1000)

                # Alert image with bbox
                alert_img = annotate_frame(frame, all_dets)
                fname = f"{ALERT_DIR}/ALERT_{class_name}_H{h_deg}_V{v_deg}_{ts}.jpg"
                cv2.imwrite(fname, alert_img)

                # Burst
                burst_dir = os.path.join(ALERT_DIR, f"burst_{ts}")
                os.makedirs(burst_dir, exist_ok=True)
                for bi in range(10):
                    for _ in range(2): self.cam.grab()
                    ret, bf = self.cam.grab()
                    if ret and bf is not None:
                        cv2.imwrite(f"{burst_dir}/frame_{bi:03d}.jpg", annotate_frame(bf, []))
                    time.sleep(0.03)

                print(f"  {red('🚨 报警!')} {class_name} 评分{vis_score:.2f}")
                if best_t and 'bbox' in best_t:
                    bx = best_t['bbox']
                    print(f"  🎯 bbox=({bx[0]:.0f},{bx[1]:.0f},{bx[2]:.0f},{bx[3]:.0f})")
                print(f"  📷 {fname}  锁定 H={h_deg} V={v_deg}  🎬 {burst_dir}/")
                alert_cid = 73 if class_name.startswith('摄像头') else class_id
                self.tts.speak_alert(alert_cid)
                print(f"  {cyan('t=信任 c=继续 q=退出')}")
                self._wait_user_response(class_name, class_id, rf_score, mag_s)

    def _wait_user_response(self, class_name=None, class_id=None, rf_s=None, mag_s=None):
        waited = 0
        while self.running and self.alarm_active and waited < 120:
            if select.select([sys.stdin], [], [], 0.1)[0]:
                try:
                    cmd = sys.stdin.readline().strip().lower()
                    if cmd in ('c', 'continue', '继续'):
                        self._resolve_alarm(); return
                    elif cmd in ('t', 'trust', '信任') and class_id:
                        self.trust.add(class_id, class_name, rf_s, mag_s)
                        print(green(f"  OK {class_name} -> 可信"))
                        self._resolve_alarm(); return
                    elif cmd in ('q', 'quit', '退出'):
                        self.running = False; return
                except: pass
            if self.use_voice and self.voice:
                act, text = self.voice.get_cmd(timeout=0.1)
                if act in ('start', 'continue'):
                    self.paused = False
                    if self.alarm_active: self._resolve_alarm()
                elif act == 'quit': self.running = False; return
                if text and class_id and any(w in text for w in ['信任','加入','可信']):
                    self.trust.add(class_id, class_name, rf_s, mag_s)
                    print(green(f"  OK {class_name} -> 可信(语音)"))
                    self._resolve_alarm(); return
            waited += 0.1

    def _resolve_alarm(self):
        with self.alarm_lock: self.alarm_active = False
        while not self.photo_queue.empty():
            try: self.photo_queue.get_nowait()
            except: break
        self._last_frame_hash = None
        self._rf_history = []
        self._bug_alerted = False
        self._resume_warmup = 3
        print(green("  >> 继续扫描...")); self.tts.speak('continue')

    # ===== 主循环 =====
    def run(self):
        self._center()
        if self.do_scan: threading.Thread(target=self._scan_worker, daemon=True).start()
        threading.Thread(target=self._ai_worker, daemon=True).start()
        if self.use_voice: self.voice.start()

        print(f"  {yellow('云台居中, 等待\"启动扫描\"...')}")
        if self.use_voice: print(f"  语音: {cyan('启动扫描/停止/拍照/退出')}")

        try:
            while self.running:
                if select.select([sys.stdin], [], [], 0.2)[0]:
                    try:
                        cmd = sys.stdin.readline().strip().lower()
                        if cmd in ('s', 'start', '启动扫描'):
                            self.paused = False; self._rf_history = []; self._bug_alerted = False
                            print(green("  >> 启动扫描")); self.tts.speak('start')
                        elif cmd in ('p', 'stop', '停止'):
                            self.paused = True
                            print(yellow("  || 暂停")); self.tts.speak('stop')
                        elif cmd in ('c', 'continue', '继续'):
                            self.paused = False
                            if self.alarm_active: self._resolve_alarm()
                            else: print(green("   继续")); self.tts.speak('continue')
                        elif cmd in ('photo', '拍照'):
                            import cv2
                            for _ in range(5): self.cam.grab()
                            ret, frame = self.cam.grab()
                            if ret:
                                cv2.imwrite(
                                    f"{CAPTURE_DIR}/manual_{int(time.time())}.jpg",
                                    annotate_frame(frame, []))
                                print("  photo"); self.tts.speak('photo')
                        elif cmd in ('q', 'quit', '退出'):
                            print(yellow("  退出")); break
                        elif cmd in ('status', '状态'): self._print_status()
                    except EOFError: break
                    except: pass

                if self.use_voice and self.voice:
                    act, text = self.voice.get_cmd(timeout=0.1)
                    if act in ('start', 'continue'):
                        self.paused = False; self._rf_history = []; self._bug_alerted = False
                        if self.alarm_active: self._resolve_alarm()
                    elif act == 'stop' and not self.paused:
                        self.paused = True; self.tts.speak('stop')
                    elif act == 'photo':
                        import cv2
                        for _ in range(5): self.cam.grab()
                        ret, frame = self.cam.grab()
                        if ret:
                            cv2.imwrite(
                                f"{CAPTURE_DIR}/voice_{int(time.time())}.jpg",
                                annotate_frame(frame, []))
                            self.tts.speak('photo')
                    elif act == 'quit':
                        print(yellow("  语音退出")); self.tts.speak('bye'); self.running = False
        except KeyboardInterrupt:
            print(f"\n  {yellow('中断')}")
        finally:
            self._cleanup()

    def _print_status(self):
        e = time.time() - self.stats["start_time"]
        peak_rf = max((r['rf'] for r in self._rf_history), default=0)
        print(f"\n  === 状态 ===\n  运行: {e:.0f}s  帧: {self.stats['frames']}"
              f"  报警: {self.stats['alerts']}  拍照: {self.stats.get('photos_saved',0)}"
              f"  RF峰值: {peak_rf:.2f}"
              f"\n  扫描: {'运行' if not self.paused else '暂停'}"
              f"  锁定: {'是' if self.alarm_active else '否'}"
              f"  可信: {len(self.trust.trusted)}个\n  ============\n")

    def _cleanup(self):
        print(f"\n{bold('清理...')}")
        self.running = False; self.paused = True
        if self.voice: self.voice.stop()
        self._center(); time.sleep(0.3)
        if self.pan_ok: PWM.cleanup(PAN_CHIP)
        if self.tilt_ok: PWM.cleanup(TILT_CHIP)
        self.cam.close(); self.tts.speak('bye')
        e = time.time() - self.stats["start_time"]
        print(f"{bold('已退出.')} {e:.0f}s"
              f" 帧:{self.stats['frames']} 报警:{self.stats['alerts']}"
              f" 拍照:{self.stats.get('photos_saved',0)}")
