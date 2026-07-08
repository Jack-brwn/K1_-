# -*- coding: utf-8 -*-
import os,sys,re,wave,time,queue,threading,tempfile
import numpy as np
import sounddevice as sd
from difflib import get_close_matches

sys.path.insert(0,'/home/bianbu/asr-llm-tts/src')

CMD_MAP={
    # 用"启动扫描"替代"开始扫描"，避免TTS播放"开始扫描"时被ASR误识别
    "启动扫描":"start","开启扫描":"start","开始检测":"start",
    "停止扫描":"stop","暂停扫描":"stop","暂停":"stop","停止":"stop",
    "继续扫描":"continue","继续":"continue",
    "拍照":"photo","拍一张":"photo",
    "退出":"quit","关闭":"quit",
}
SYNONYMS={"启动":"启动扫描","开启":"启动扫描","停":"停止"}
IGNORE=['的','了','吧','啊','呢','吗','哦','嗯']
MIN_CHARS=2
COOLDOWN=3.0
FUZZY=0.85

def _norm(t):
    if not t: return ""
    c=re.sub(r'[^一-龥a-zA-Z0-9]','',t)
    for w in IGNORE: c=c.replace(w,'')
    return c

def _chinese(t):
    return sum(1 for c in t if '一'<=c<='鿿')

def _detect(text):
    if not text: return None
    if _chinese(text)<MIN_CHARS: return None
    clean=_norm(text)
    if not clean: return None
    std=SYNONYMS.get(clean,clean)
    if std in CMD_MAP: return CMD_MAP[std]
    for kw,act in CMD_MAP.items():
        if kw in clean: return act
    possible=get_close_matches(clean,CMD_MAP.keys(),n=1,cutoff=FUZZY)
    if possible: return CMD_MAP[possible[0]]
    return None

class VoiceRecognizer:
    def __init__(self,sample_rate=16000,chunk_sec=2.0):
        self.sr=sample_rate
        self.chunk_sec=chunk_sec
        self.chunk_samples=int(self.sr*self.chunk_sec)
        self.asr=None
        self.model=None
        self.running=False
        self.cmd_queue=queue.Queue()
        self._audio_buffer=[]
        self._last_cmd={}
        self._init_asr()

    def _init_asr(self):
        print("  [语音] 加载ASR模型...",end="",flush=True)
        try:
            from asr import AsrModel
            self.asr=AsrModel(model_dir='/home/bianbu/asr-llm-tts/src/asr/models')
            self.model=self.asr
            print(" OK (实时模式)")
        except Exception as e:
            print(" 失败: "+str(e))

    def start(self):
        if not self.asr: return False
        self.running=True
        threading.Thread(target=self._listen_loop,daemon=True).start()
        return True

    def _audio_callback(self,indata,frames,time_info,status):
        if status: print("  [音频] "+str(status),flush=True)
        self._audio_buffer.append(indata.copy())

    def _save_and_recognize(self):
        if not self.asr: return
        if len(self._audio_buffer)==0: return
        audio=np.concatenate(self._audio_buffer,axis=0)
        self._audio_buffer=[]
        if len(audio)<self.sr*1.0: return
        tmp=tempfile.NamedTemporaryFile(delete=False,suffix='.wav')
        with wave.open(tmp.name,'wb') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(self.sr)
            wf.writeframes(audio.tobytes())
        try:
            text=self.asr(tmp.name).strip()
            if text:
                print()
                print("  [语音识别] "+text)
                act=_detect(text)
                if act:
                    now=time.time()
                    last=self._last_cmd.get(act,0)
                    if now-last<COOLDOWN: return
                    self._last_cmd[act]=now
                    print("  [语音指令] -> "+act)
                    self.cmd_queue.put((act,text))
        except Exception:
            pass
        finally:
            try: os.unlink(tmp.name)
            except: pass

    def _listen_loop(self):
        print("  [语音] 实时监听已开启 (无需按键)")
        self._audio_buffer=[]
        try:
            with sd.InputStream(samplerate=self.sr,channels=1,dtype='int16',callback=self._audio_callback):
                last_check=time.time()
                while self.running:
                    time.sleep(0.2)
                    now=time.time()
                    if now-last_check>=self.chunk_sec:
                        self._save_and_recognize()
                        last_check=now
        except Exception as e:
            print("  [语音] 音频异常: "+str(e))

    def stop(self): self.running=False

    def get_cmd(self,timeout=0.3):
        try: return self.cmd_queue.get(timeout=timeout)
        except queue.Empty: return None,None

    def match(self,text): return _detect(text)
