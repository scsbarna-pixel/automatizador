# -*- coding: utf-8 -*-
import os
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QSlider, QHBoxLayout, 
                               QPushButton, QDialogButtonBox, QMessageBox)
from PySide6.QtCore import Qt, QTimer, QObject

class CueWorker(QObject):
    def __init__(self, filepath, device):
        super().__init__()
        self.filepath = filepath
        self.device = device
        self.data = None; self.fs = 44100; self.current_frame = 0
        self.is_playing = False; self.stream = None; self.lock = threading.Lock()

    def load(self):
        try:
            data, fs = sf.read(self.filepath, dtype='float32')
            if data.ndim == 1: data = np.column_stack((data, data))
            self.data = data; self.fs = fs
            return True
        except: return False

    def play(self):
        if self.data is None: return
        self.is_playing = True
        try:
            self.stream = sd.OutputStream(samplerate=self.fs, channels=2, device=self.device, callback=self.cb, blocksize=2048)
            self.stream.start()
        except: self.is_playing = False

    def pause(self):
        self.is_playing = False
        if self.stream: self.stream.stop(); self.stream.close()

    def seek(self, percent):
        if self.data is None: return
        with self.lock: self.current_frame = int(len(self.data) * percent)

    def cb(self, out, fr, t, s):
        if not self.is_playing: out.fill(0); raise sd.CallbackStop
        with self.lock:
            chk = len(out)
            if self.current_frame + chk > len(self.data): out.fill(0); self.is_playing = False; raise sd.CallbackStop
            else: out[:] = self.data[self.current_frame:self.current_frame+chk]; self.current_frame += chk

    def get_pos(self): return (self.current_frame / len(self.data)) if (self.data is not None and len(self.data)>0) else 0
    def get_time_str(self):
        if self.data is None: return "00:00"
        c = self.current_frame/self.fs; t = len(self.data)/self.fs
        return f"{int(c//60):02}:{int(c%60):02} / {int(t//60):02}:{int(t%60):02}"

class CuePlayerDialog(QDialog):
    def __init__(self, parent, filepath, device_id, current_offset=0):
        super().__init__(parent)
        self.setWindowTitle("Pre-escucha (CUE) - Fijar Inicio")
        self.resize(500, 160)
        self.offset = current_offset
        self.worker = CueWorker(filepath, device_id)
        
        if not self.worker.load():
            QMessageBox.critical(self, "Error", "No se pudo cargar el audio.")
            return

        l = QVBoxLayout(self)
        l.addWidget(QLabel(f"<b>Editando:</b> {os.path.basename(filepath)}"))
        self.sl = QSlider(Qt.Horizontal); self.sl.setRange(0, 1000)
        self.sl.sliderPressed.connect(lambda: setattr(self, 'seeking', True))
        self.sl.sliderReleased.connect(self.do_seek)
        l.addWidget(self.sl)
        self.lbl = QLabel("00:00"); self.lbl.setAlignment(Qt.AlignCenter)
        self.lbl.setStyleSheet("font-size: 14pt; font-weight:bold; color: #000088;")
        l.addWidget(self.lbl)
        h = QHBoxLayout(); self.bp = QPushButton("▶ Play"); self.bp.clicked.connect(self.tgl)
        bs = QPushButton("⏹ Stop"); bs.clicked.connect(self.stop_close)
        h.addWidget(self.bp); h.addWidget(bs); l.addLayout(h)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Fijar Punto de Inicio")
        bb.accepted.connect(self.save); bb.rejected.connect(self.stop_close)
        l.addWidget(bb)
        self.seeking = False
        self.tm = QTimer(self); self.tm.timeout.connect(self.upd); self.tm.start(100)
        self.tgl()

    def tgl(self):
        if self.worker.is_playing: self.worker.pause(); self.bp.setText("▶ Play")
        else: self.worker.play(); self.bp.setText("⏸ Pausa")
    def do_seek(self): self.worker.seek(self.sl.value()/1000); self.seeking = False
    def upd(self):
        self.lbl.setText(self.worker.get_time_str())
        if not self.seeking: self.sl.setValue(int(self.worker.get_pos()*1000))
        if not self.worker.is_playing: self.bp.setText("▶ Play")
    def save(self):
        if self.worker.fs > 0: self.offset = self.worker.current_frame / self.worker.fs
        self.stop_close(save=True)
    def stop_close(self, save=False):
        self.worker.pause(); self.tm.stop()
        if save: self.accept()
        else: self.reject()
    def closeEvent(self, e): self.worker.pause(); e.accept()