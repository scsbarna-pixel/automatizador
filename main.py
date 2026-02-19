"""Máquina principal del programa."""

import tkinter as tk

from modulos.volumen import VolumeController


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Automatizador")

        self.volume = VolumeController()

        self.mic_button = tk.Button(root, text="MIC OFF", width=20, command=self.on_mic_click)
        self.mic_button.pack(padx=20, pady=20)

    def on_mic_click(self):
        mic_on = self.volume.toggle_mic_mode()
        self.mic_button.config(text="MIC ON" if mic_on else "MIC OFF")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
