import os
import tkinter as tk
from tkinter import filedialog, messagebox

# --- VU meter desde salida de audio por defecto (Windows Core Audio) ---
from ctypes import POINTER, cast
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioMeterInformation

# --- Reproducción con VLC ---
import vlc


AUDIO_EXTS = (".mp3", ".wav", ".wma", ".aac", ".flac", ".ogg", ".m4a")


class SystemPeakMeter:
    """Lee el peak (0..1) del dispositivo de reproducción por defecto."""
    def __init__(self):
        device = AudioUtilities.GetSpeakers()
        interface = device.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
        self.meter = cast(interface, POINTER(IAudioMeterInformation))

    def get_peak(self) -> float:
        try:
            v = float(self.meter.GetPeakValue())
            if v < 0: v = 0.0
            if v > 1: v = 1.0
            return v
        except Exception:
            return 0.0


class PlaylistPopup(tk.Toplevel):
    def __init__(self, master, on_load_callback):
        super().__init__(master)
        self.title("Lista (Aceptados)")
        self.geometry("520x380")
        self.attributes("-topmost", True)

        self.on_load_callback = on_load_callback

        self.accepted = tk.Listbox(self, selectmode=tk.SINGLE)
        self.accepted.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        btns = tk.Frame(self)
        btns.pack(fill=tk.X, padx=10, pady=(0, 10))

        tk.Button(btns, text="Añadir canciones", command=self.add_files, width=16).pack(side=tk.LEFT, padx=5)
        tk.Button(btns, text="Quitar", command=self.remove_selected, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btns, text="Cargar seleccionada", command=self.load_selected, width=18).pack(side=tk.RIGHT, padx=5)

    def add_files(self):
        files = filedialog.askopenfilenames(
            title="Elige canciones",
            filetypes=[("Audio", "*.mp3 *.wav *.wma *.aac *.flac *.ogg *.m4a"), ("Todos", "*.*")]
        )
        for f in files:
            if f and os.path.splitext(f)[1].lower() in AUDIO_EXTS:
                # evitar duplicados
                existing = set(self.accepted.get(0, tk.END))
                if f not in existing:
                    self.accepted.insert(tk.END, f)

    def remove_selected(self):
        sel = self.accepted.curselection()
        if not sel:
            return
        self.accepted.delete(sel[0])

    def load_selected(self):
        items = list(self.accepted.get(0, tk.END))
        if not items:
            messagebox.showinfo("Lista vacía", "Añade canciones a 'Aceptados' primero.")
            return
        sel = self.accepted.curselection()
        idx = sel[0] if sel else 0
        self.on_load_callback(items, idx)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Modular Music Player (Python)")
        self.geometry("640x220")
        self.resizable(False, False)

        # VLC
        self.vlc_instance = vlc.Instance("--no-video")
        self.player = self.vlc_instance.media_player_new()

        # Playlist
        self.accepted_list = []
        self.index = -1
        self.current_path = None

        # VU Meter
        self.meter = SystemPeakMeter()
        self.smooth = 0.0  # suavizado
        self.vu_fps_ms = 33  # ~30 FPS (ligero)

        # UI
        self.track_var = tk.StringVar(value="(sin canción)")
        tk.Label(self, textvariable=self.track_var, anchor="w").pack(fill=tk.X, padx=12, pady=(10, 4))

        self.canvas = tk.Canvas(self, height=30, bg="black", highlightthickness=1, highlightbackground="#444")
        self.canvas.pack(fill=tk.X, padx=12, pady=(0, 12))
        self.vu_rect = self.canvas.create_rectangle(0, 0, 0, 30, fill="#34c759", width=0)

        btns = tk.Frame(self)
        btns.pack(fill=tk.X, padx=12)

        tk.Button(btns, text="CUE", width=10, command=self.cue).pack(side=tk.LEFT, padx=6)
        tk.Button(btns, text="STOP", width=10, command=self.stop).pack(side=tk.LEFT, padx=6)
        tk.Button(btns, text="PLAY", width=10, command=self.play).pack(side=tk.LEFT, padx=6)
        tk.Button(btns, text="SIGUIENTE", width=12, command=self.next_track).pack(side=tk.LEFT, padx=6)
        tk.Button(btns, text="LISTA", width=10, command=self.open_list).pack(side=tk.RIGHT, padx=6)

        self.popup = None

        # Arrancar bucle del VU
        self.after(self.vu_fps_ms, self.update_vu)

    def open_list(self):
        if self.popup and self.popup.winfo_exists():
            self.popup.lift()
            return
        self.popup = PlaylistPopup(self, self.on_load_from_popup)

    def on_load_from_popup(self, items, idx):
        self.accepted_list = items
        self.index = idx
        self.load_track(self.accepted_list[self.index])

    def load_track(self, path):
        self.current_path = path
        self.track_var.set(os.path.basename(path))
        media = self.vlc_instance.media_new(path)
        self.player.set_media(media)

    def play(self):
        if not self.current_path:
            if self.accepted_list:
                if self.index < 0:
                    self.index = 0
                self.load_track(self.accepted_list[self.index])
            else:
                messagebox.showinfo("Sin canción", "Pulsa LISTA y añade canciones a 'Aceptados'.")
                return
        self.player.play()

    def stop(self):
        # stop y vuelve a 0 para que sea “STOP real”
        try:
            self.player.stop()
        except Exception:
            pass

    def cue(self):
        # CUE simple: vuelve al inicio (0 ms). Si está parado, deja preparado.
        try:
            self.player.set_time(0)
        except Exception:
            pass

    def next_track(self):
        if not self.accepted_list:
            return
        self.index = (self.index + 1) % len(self.accepted_list)
        self.load_track(self.accepted_list[self.index])
        self.play()

    def update_vu(self):
        peak = self.meter.get_peak()
        # suavizado exponencial (vu suave, nada agresivo)
        self.smooth = (self.smooth * 0.85) + (peak * 0.15)

        w = int(self.canvas.winfo_width() * self.smooth)
        self.canvas.coords(self.vu_rect, 0, 0, w, 30)

        self.after(self.vu_fps_ms, self.update_vu)


if __name__ == "__main__":
    App().mainloop()
