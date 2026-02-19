# -*- coding: utf-8 -*-
import sys
import time
import requests
from PySide6.QtWidgets import QApplication, QLabel, QWidget, QHBoxLayout
from PySide6.QtCore import QThread, Signal, Qt

# --- 1. IMPORTAMOS TU "CAJA NEGRA" (Tu programa original) ---
# Nota: Asumimos que tu archivo original se llama 'main34.py'
try:
    import main34 as core
except ImportError:
    print("❌ ERROR CRÍTICO: No encuentro el archivo 'main34.py' en esta carpeta.")
    print("Asegúrate de que este archivo (oyentes.py) y 'main34.py' estén juntos.")
    input("Presiona ENTER para salir...")
    sys.exit()

# --- 2. HILO DE TRABAJO (El "espía" de SonicPanel) ---
# Este trabajador funcionará en segundo plano para no congelar la música
class ListenerWorker(QThread):
    update_signal = Signal(str)

    def __init__(self, api_url):
        super().__init__()
        self.api_url = api_url
        self.running = True

    def run(self):
        while self.running:
            try:
                # Consultamos a SonicPanel
                response = requests.get(self.api_url, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    # Buscamos el dato 'listeners' (oyentes actuales)
                    # Si no existe, usamos '0'
                    count = data.get("listeners", "0")
                    self.update_signal.emit(f"🎧 {count} Oyentes")
                else:
                    self.update_signal.emit("⚠️ API Err")
            
            except Exception as e:
                # Si falla la conexión (internet caído, etc), no rompemos nada
                # print(f"Error conexión: {e}") 
                self.update_signal.emit("📡 Conectando...")

            # Esperamos 15 segundos antes de volver a preguntar
            # Lo hacemos en pasos de 1s para poder parar el hilo rápido si cierras la app
            for _ in range(15):
                if not self.running: break
                time.sleep(1)

    def stop(self):
        self.running = False

# --- 3. LA VENTANA VITAMINADA (Herencia) ---
# Aquí cogemos tu ventana original y le "pegamos" el contador
class RadioConOyentes(core.MainWindow):
    def __init__(self):
        # 1. Cargamos toda la maquinaria original de main34.py
        super().__init__()
        self.setWindowTitle("ZaraClone Radio Automation (Modo Producción + Oyentes)")

        # 2. Configuración de tu API
        self.api_url = "https://sonic.sistemahost.es/cp/get_info.php?p=8062"

        # 3. Creamos la etiqueta Visual para los oyentes
        self.lbl_oyentes = QLabel("📡 Cargando...")
        self.lbl_oyentes.setStyleSheet("""
            font-size: 18px; 
            font-weight: bold; 
            color: #27ae60; 
            border: 1px solid #ccc; 
            border-radius: 4px;
            padding: 4px 8px;
            background-color: #eafaf1;
            margin-right: 10px;
        """)
        
        # 4. INYECCIÓN QUIRÚRGICA: Buscamos dónde ponerlo
        # Tu reloj original se llama 'lbl_clk' en main34.py
        # Vamos a buscar su "padre" (el layout horizontal) y nos colamos ahí.
        try:
            # Buscamos el layout donde vive el reloj
            layout_reloj = self.lbl_clk.parentWidget().layout()
            
            # Buscamos la posición del reloj para ponernos justo antes
            index_reloj = layout_reloj.indexOf(self.lbl_clk)
            
            # Nos insertamos justo antes del reloj
            # (Si prefieres después, cambia index_reloj por index_reloj + 1)
            layout_reloj.insertWidget(index_reloj, self.lbl_oyentes)
            
        except Exception as e:
            print(f"No pude inyectar el contador automáticamente: {e}")
            # Plan B: Si falla la inyección, lo ponemos flotante o arriba (opcional)

        # 5. Arrancamos el hilo espía
        self.worker = ListenerWorker(self.api_url)
        self.worker.update_signal.connect(self.actualizar_etiqueta)
        self.worker.start()

    def actualizar_etiqueta(self, texto):
        self.lbl_oyentes.setText(texto)

    # Cuando cerramos la ventana, apagamos el hilo limpiamente
    def closeEvent(self, event):
        self.worker.stop()
        self.worker.wait()
        super().closeEvent(event)

# --- 4. LANZADOR ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Arrancamos nuestra versión modificada en lugar de la original
    ventana = RadioConOyentes()
    ventana.showMaximized()
    
    sys.exit(app.exec())