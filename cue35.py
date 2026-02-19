# -*- coding: utf-8 -*-
import os
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QSlider, QHBoxLayout, 
                               QPushButton, QDialogButtonBox, QMessageBox)
from PySide6.QtCore import Qt, QTimer, QObject

def read_audio(filepath):
    try:
        data, fs = sf.read(filepath, dtype='float32')
        return data, fs
    except:
        return None, 0

class CueWorker(QObject):
    def __init__(self, filepath, device):
        super().__init__()
        self.filepath = filepath
        self.device = device
        self.data = None
        self.fs = 44100
        self.current_frame = 0
        self.is_playing = False
        self.stream = None
        self.lock = threading.Lock()

    def load(self):
        d, f = read_audio(self.filepath)
        if d is None: return False
        if d.ndim == 1: d = np.column_stack((d, d))
        self.data = d
        self.fs = f
        return True

    def play(self):
        if self.data is None: return
        self.is_playing = True
        try:
            self.stream = sd.OutputStream(
                samplerate=self.fs, channels=2, device=self.device,
                callback=self.callback, blocksize=2048
            )
            self.stream.start()
        except Exception as e:
            print("Error stream CUE:", e)
            self.is_playing = False

    def pause(self):
        self.is_playing = False
        if self.stream:
            self.stream.stop(); self.stream.close()

    def seek(self, percent):
        if self.data is None: return
        with self.lock:
            self.current_frame = int(len(self.data) * percent)

    def callback(self, outdata, frames, time, status):
        if not self.is_playing:
            outdata.fill(0); raise sd.CallbackStop
        with self.lock:
            chunksize = len(outdata)
            if self.current_frame + chunksize > len(self.data):
                outdata.fill(0); self.is_playing = False; raise sd.CallbackStop
            else:
                outdata[:] = self.data[self.current_frame:self.current_frame+chunksize]
                self.current_frame += chunksize

    def get_pos(self):
        if self.data is None or len(self.data) == 0: return 0
        return self.current_frame / len(self.data)
    
    def get_time_str(self):
        if self.data is None: return "00:00"
        cur = self.current_frame / self.fs
        tot = len(self.data) / self.fs
        return f"{int(cur//60):02}:{int(cur%60):02} / {int(tot//60):02}:{int(tot%60):02}"

class CuePlayerDialog(QDialog):
    def __init__(self, parent, filepath, device_id, current_offset=0):
        super().__init__(parent)
        self.setWindowTitle("Pre-escucha (CUE) - Fijar Inicio")
        self.resize(500, 150)
        self.offset = current_offset
        self.worker = CueWorker(filepath, device_id)
        
        if not self.worker.load():
            QMessageBox.critical(self, "Error", "No se pudo cargar el audio.")
            return

        l = QVBoxLayout(self)
        l.addWidget(QLabel(f"<b>Editando:</b> {os.path.basename(filepath)}"))
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.sliderPressed.connect(self.seek_start)
        self.slider.sliderReleased.connect(self.seek_end)
        l.addWidget(self.slider)
        
        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setAlignment(Qt.AlignCenter)
        self.lbl_time.setStyleSheet("font-size: 14pt; font-weight:bold; color: #000088;")
        l.addWidget(self.lbl_time)

        h = QHBoxLayout()
        self.btn_play = QPushButton("▶ Play"); self.btn_play.clicked.connect(self.toggle_play)
        btn_stop = QPushButton("⏹ Stop"); btn_stop.clicked.connect(self.stop_close)
        h.addWidget(self.btn_play); h.addWidget(btn_stop); l.addLayout(h)
        
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Fijar Punto de Inicio")
        bb.accepted.connect(self.save); bb.rejected.connect(self.stop_close)
        l.addWidget(bb)
        
        self.seeking = False
        self.timer = QTimer(self); self.timer.timeout.connect(self.update_ui); self.timer.start(100)
        self.toggle_play()

    def toggle_play(self):
        if self.worker.is_playing:
            self.worker.pause(); self.btn_play.setText("▶ Play")
        else:
            self.worker.play(); self.btn_play.setText("⏸ Pausa")

    def seek_start(self): self.seeking = True
    def seek_end(self):
        self.worker.seek(self.slider.value() / 1000); self.seeking = False

    def update_ui(self):
        if self.worker.data is not None:
            self.lbl_time.setText(self.worker.get_time_str())
            if not self.seeking: self.slider.setValue(int(self.worker.get_pos() * 1000))
            if not self.worker.is_playing and self.btn_play.text() == "⏸ Pausa": self.btn_play.setText("▶ Play")

    def save(self):
        if self.worker.fs > 0: self.offset = self.worker.current_frame / self.worker.fs
        self.stop_close(save=True)

    def stop_close(self, save=False):
        self.worker.pause(); self.timer.stop()
        if save: self.accept()
        else: self.reject()

    def closeEvent(self, e): self.worker.pause(); e.accept()