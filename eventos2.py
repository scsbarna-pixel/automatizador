# -*- coding: utf-8 -*-
import json
import os
import copy
from datetime import datetime
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableView, 
                               QLabel, QLineEdit, QGroupBox, QRadioButton, QCheckBox, 
                               QTimeEdit, QDateEdit, QSpinBox, QComboBox, QStackedWidget, 
                               QFileDialog, QDialogButtonBox, QHeaderView, QGridLayout, 
                               QStyledItemDelegate, QStyle, QWidget, QMessageBox)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QTime, QDate, QEvent, QRect
import sounddevice as sd

# --- CORRECCIÓN DE RUTA PARA EVITAR PÉRDIDA DE DATOS ---
# Esto asegura que el archivo se crea siempre donde está el script .py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EVENTS_FILE = os.path.join(BASE_DIR, "events_db.json")

class HourGridDialog(QDialog):
    def __init__(self, parent=None, selected_hours=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Horas")
        self.selected_hours = selected_hours or []
        self.checkboxes = []
        l = QVBoxLayout(self)
        g = QGridLayout()
        for i in range(24):
            c = QCheckBox(f"{i:02}:00")
            if i in self.selected_hours:
                c.setChecked(True)
            self.checkboxes.append(c)
            g.addWidget(c, i//4, i%4)
        l.addLayout(g)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        l.addWidget(bb)

    def get_hours(self):
        return [i for i, c in enumerate(self.checkboxes) if c.isChecked()]

class EventEditorDialog(QDialog):
    def __init__(self, parent=None, event_data=None):
        super().__init__(parent)
        self.setWindowTitle("Editor de Eventos")
        self.resize(650, 500)
        self.event_data = event_data or {}
        self.other_hours_list = []
        self.setup_ui()
        if self.event_data:
            self.load_ui_data()

    def setup_ui(self):
        l = QVBoxLayout(self)
        
        # Nombre
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Nombre:"))
        self.txt_name = QLineEdit()
        h1.addWidget(self.txt_name)
        l.addLayout(h1)

        # Configuración Principal
        h_main = QHBoxLayout()
        
        # Periodicidad
        gp = QGroupBox("Periodicidad")
        vp = QVBoxLayout()
        self.rb_once = QRadioButton("Una vez")
        self.rb_hourly = QRadioButton("Cada hora")
        self.rb_grid = QRadioButton("Parrilla...")
        self.rb_grid.toggled.connect(self.open_grid)
        self.rb_once.setChecked(True)
        vp.addWidget(self.rb_once)
        vp.addWidget(self.rb_hourly)
        vp.addWidget(self.rb_grid)
        gp.setLayout(vp)
        h_main.addWidget(gp)

        # Hora y Fecha
        gd = QGroupBox("Hora / Fecha")
        vd = QVBoxLayout()
        h_time = QHBoxLayout()
        self.time_edit = QTimeEdit(QTime.currentTime())
        self.time_edit.setDisplayFormat("HH:mm:ss")
        h_time.addWidget(QLabel("Hora:"))
        h_time.addWidget(self.time_edit)
        vd.addLayout(h_time)
        
        self.date_edit = QDateEdit(QDate.currentDate())
        vd.addWidget(QLabel("Fecha (Solo 'Una vez'):"))
        vd.addWidget(self.date_edit)
        
        h_exp = QHBoxLayout()
        self.chk_expire = QCheckBox("Expirar:")
        self.date_expire = QDateEdit(QDate.currentDate().addDays(365))
        h_exp.addWidget(self.chk_expire)
        h_exp.addWidget(self.date_expire)
        vd.addLayout(h_exp)
        gd.setLayout(vd)
        h_main.addWidget(gd)
        l.addLayout(h_main)

        # Opciones y Dias
        h_mid = QHBoxLayout()
        
        g_pri = QGroupBox("Opciones")
        vp2 = QVBoxLayout()
        self.chk_immediate = QCheckBox("Inmediato (Cortar)")
        self.chk_overlay = QCheckBox("Sonar encima (Overlay)")
        
        h_wait = QHBoxLayout()
        self.chk_wait = QCheckBox("Espera máx (min):")
        self.spin_wait = QSpinBox()
        self.spin_wait.setValue(10)
        h_wait.addWidget(self.chk_wait)
        h_wait.addWidget(self.spin_wait)
        
        h_prio = QHBoxLayout()
        h_prio.addWidget(QLabel("Prioridad:"))
        self.rb_prio_high = QRadioButton("Alta")
        self.rb_prio_low = QRadioButton("Baja")
        self.rb_prio_low.setChecked(True)
        h_prio.addWidget(self.rb_prio_high)
        h_prio.addWidget(self.rb_prio_low)

        vp2.addWidget(self.chk_immediate)
        vp2.addWidget(self.chk_overlay)
        vp2.addLayout(h_wait)
        vp2.addLayout(h_prio)
        g_pri.setLayout(vp2)
        h_mid.addWidget(g_pri)

        g_days = QGroupBox("Días de la semana")
        gl = QGridLayout()
        self.days_checks = []
        dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        for i, d in enumerate(dias):
            c = QCheckBox(d)
            c.setChecked(True)
            self.days_checks.append(c)
            gl.addWidget(c, i//4, i%4)
        g_days.setLayout(gl)
        h_mid.addWidget(g_days)
        l.addLayout(h_mid)

        # Contenido
        gt = QGroupBox("Contenido")
        vt = QVBoxLayout()
        h_type = QHBoxLayout()
        self.rb_file = QRadioButton("Fichero")
        self.rb_rnd = QRadioButton("Carpeta Random")
        self.rb_time = QRadioButton("Hora")
        self.rb_temp = QRadioButton("Temperatura")
        self.rb_sat = QRadioButton("Satélite")
        self.rb_file.setChecked(True)
        h_type.addWidget(self.rb_file)
        h_type.addWidget(self.rb_rnd)
        h_type.addWidget(self.rb_time)
        h_type.addWidget(self.rb_temp)
        h_type.addWidget(self.rb_sat)
        vt.addLayout(h_type)

        self.stack = QStackedWidget()
        
        # Pagina Fichero
        w0 = QWidget()
        l0 = QHBoxLayout(w0)
        self.txt_file = QLineEdit()
        b0 = QPushButton("...")
        b0.clicked.connect(lambda: self.browse(False))
        l0.addWidget(self.txt_file)
        l0.addWidget(b0)
        self.stack.addWidget(w0)
        
        # Pagina Random
        w1 = QWidget()
        l1 = QHBoxLayout(w1)
        self.txt_folder = QLineEdit()
        b1 = QPushButton("...")
        b1.clicked.connect(lambda: self.browse(True))
        l1.addWidget(self.txt_folder)
        l1.addWidget(b1)
        self.stack.addWidget(w1)
        
        # Pagina Info
        self.stack.addWidget(QLabel("Locución automática (requiere internet/gTTS)"))
        
        # Pagina Satelite
        w3 = QWidget()
        l3 = QHBoxLayout(w3)
        self.combo_sat = QComboBox()
        try:
            devs = sd.query_devices()
            for i, d in enumerate(devs):
                if d['max_input_channels'] > 0:
                    self.combo_sat.addItem(f"{i}: {d['name']}", i)
        except: pass
        self.dur_sat = QTimeEdit(QTime(0, 30, 0))
        self.dur_sat.setDisplayFormat("HH:mm:ss")
        l3.addWidget(QLabel("Entrada:"))
        l3.addWidget(self.combo_sat)
        l3.addWidget(QLabel("Duración:"))
        l3.addWidget(self.dur_sat)
        self.stack.addWidget(w3)

        vt.addWidget(self.stack)
        gt.setLayout(vt)
        l.addWidget(gt)

        self.rb_file.toggled.connect(lambda: self.stack.setCurrentIndex(0))
        self.rb_rnd.toggled.connect(lambda: self.stack.setCurrentIndex(1))
        self.rb_time.toggled.connect(lambda: self.stack.setCurrentIndex(2))
        self.rb_temp.toggled.connect(lambda: self.stack.setCurrentIndex(2))
        self.rb_sat.toggled.connect(lambda: self.stack.setCurrentIndex(3))

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        l.addWidget(bb)

    def open_grid(self, checked):
        if checked:
            dlg = HourGridDialog(self, self.other_hours_list)
            if dlg.exec():
                self.other_hours_list = dlg.get_hours()

    def browse(self, folder=False):
        if folder:
            d = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta")
            if d: self.txt_folder.setText(d)
        else:
            d, _ = QFileDialog.getOpenFileName(self, "Seleccionar Audio", "", "Audio (*.mp3 *.wav)")
            if d: self.txt_file.setText(d)

    def load_ui_data(self):
        d = self.event_data
        self.txt_name.setText(d.get('name', ''))
        
        per = d.get('periodicity', 'once')
        if per == 'hourly': self.rb_hourly.setChecked(True)
        elif per == 'other': 
            self.rb_grid.setChecked(True)
            self.other_hours_list = d.get('other_hours', [])
        else: self.rb_once.setChecked(True)
        
        self.time_edit.setTime(QTime.fromString(d.get('time', '00:00:00'), "HH:mm:ss"))
        self.chk_immediate.setChecked(d.get('immediate', False))
        self.chk_overlay.setChecked(d.get('overlay', False))
        
        extra = d.get('extra', {})
        self.chk_wait.setChecked(extra.get('wait_enabled', False))
        self.spin_wait.setValue(extra.get('wait_minutes', 10))
        self.chk_expire.setChecked(d.get('expire', False))
        
        if d.get('priority') == 'high':
            self.rb_prio_high.setChecked(True)
        
        days = d.get('days', [True]*7)
        for i, c in enumerate(self.days_checks):
            if i < len(days): c.setChecked(days[i])
            
        typ = d.get('type', 'file')
        val = d.get('value', '')
        
        if typ == 'file': 
            self.rb_file.setChecked(True)
            self.txt_file.setText(val)
        elif typ == 'random': 
            self.rb_rnd.setChecked(True)
            self.txt_folder.setText(val)
        elif typ == 'time': 
            self.rb_time.setChecked(True)
        elif typ == 'temp': 
            self.rb_temp.setChecked(True)
        elif typ == 'sat':
            self.rb_sat.setChecked(True)
            idx = self.combo_sat.findData(val)
            if idx >= 0: self.combo_sat.setCurrentIndex(idx)

    def get_data(self):
        typ = 'file'
        val = self.txt_file.text()
        if self.rb_rnd.isChecked():
            typ = 'random'
            val = self.txt_folder.text()
        elif self.rb_time.isChecked():
            typ = 'time'
            val = ''
        elif self.rb_temp.isChecked():
            typ = 'temp'
            val = ''
        elif self.rb_sat.isChecked():
            typ = 'sat'
            val = self.combo_sat.currentData()
            
        per = 'once'
        if self.rb_hourly.isChecked(): per = 'hourly'
        elif self.rb_grid.isChecked(): per = 'other'
        
        return {
            "name": self.txt_name.text(),
            "time": self.time_edit.time().toString("HH:mm:ss"),
            "periodicity": per,
            "other_hours": self.other_hours_list,
            "days": [c.isChecked() for c in self.days_checks],
            "immediate": self.chk_immediate.isChecked(),
            "overlay": self.chk_overlay.isChecked(),
            "priority": "high" if self.rb_prio_high.isChecked() else "low",
            "expire": self.chk_expire.isChecked(),
            "type": typ,
            "value": val,
            "extra": {
                "wait_enabled": self.chk_wait.isChecked(),
                "wait_minutes": self.spin_wait.value(),
                "duration": self.dur_sat.time().toString("HH:mm:ss")
            },
            "active": self.event_data.get('active', True)
        }

class EventsTableModel(QAbstractTableModel):
    def __init__(self, events):
        super().__init__()
        self.events = events
        self.headers = ["Hora", "Tipo", "Nombre", "Días", "Activo"]

    def rowCount(self, p=QModelIndex()): return len(self.events)
    def columnCount(self, p=QModelIndex()): return 5
    
    def data(self, index, role):
        if not index.isValid(): return None
        e = self.events[index.row()]
        if role == Qt.DisplayRole:
            if index.column() == 0: return e['time']
            if index.column() == 1: return e['type'].upper()
            if index.column() == 2: return e.get('name', '')
            if index.column() == 3: return "LMXJVSD" 
            if index.column() == 4: return "SI" if e.get('active', True) else "NO"
        return None

    def headerData(self, s, o, r):
        if r == Qt.DisplayRole and o == Qt.Horizontal:
            return self.headers[s]
        return None

    def toggle_active(self, row):
        self.events[row]['active'] = not self.events[row].get('active', True)
        self.dataChanged.emit(self.index(row, 0), self.index(row, 4))
        # AUTO GUARDADO AL HACER CLICK EN ACTIVO
        try:
            with open(EVENTS_FILE, 'w') as f: json.dump(self.events, f)
        except Exception as e: print(f"Error guardando estado: {e}")

class EventDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if index.column() == 4:
            painter.save()
            data = index.data(Qt.DisplayRole)
            active = (data == "SI")
            if option.state & QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())
            painter.drawText(option.rect, Qt.AlignCenter, "✅" if active else "⬛")
            painter.restore()
        else:
            super().paint(painter, option, index)

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonRelease and index.column() == 4:
            model.toggle_active(index.row())
            return True
        return False

class EventsManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestor de Eventos")
        self.resize(750, 400)
        self.events = self.load()
        self.setup()

    def setup(self):
        l = QVBoxLayout(self)
        self.table = QTableView()
        self.model = EventsTableModel(self.events)
        self.table.setModel(self.model)
        self.table.setItemDelegate(EventDelegate(self.table))
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        l.addWidget(self.table)
        
        bl = QHBoxLayout()
        b_add = QPushButton("Añadir")
        b_add.clicked.connect(self.add)
        b_dup = QPushButton("Duplicar") # Nuevo botón
        b_dup.clicked.connect(self.duplicate)
        b_edit = QPushButton("Editar")
        b_edit.clicked.connect(self.edit)
        b_del = QPushButton("Borrar")
        b_del.clicked.connect(self.delete)
        b_save = QPushButton("Cerrar")
        b_save.clicked.connect(self.accept)
        
        bl.addWidget(b_add)
        bl.addWidget(b_dup) # Añadir al layout
        bl.addWidget(b_edit)
        bl.addWidget(b_del)
        bl.addStretch()
        bl.addWidget(b_save)
        l.addLayout(bl)

    def load(self):
        if os.path.exists(EVENTS_FILE):
            try:
                with open(EVENTS_FILE, 'r') as f: return json.load(f)
            except: return []
        return []

    # FUNCIÓN CENTRAL DE GUARDADO
    def save_db(self):
        try:
            with open(EVENTS_FILE, 'w') as f: json.dump(self.events, f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {e}")

    def add(self):
        dlg = EventEditorDialog(self)
        if dlg.exec():
            self.events.append(dlg.get_data())
            self.model.layoutChanged.emit()
            self.save_db() # Auto guardado

    def duplicate(self):
        idx = self.table.selectionModel().currentIndex()
        if idx.isValid():
            # Crear copia profunda para no modificar el original por referencia
            new_event = copy.deepcopy(self.events[idx.row()])
            new_event['name'] = f"{new_event.get('name','')} (Copia)"
            
            # Abrimos el editor con los datos copiados para que puedas cambiar la hora
            dlg = EventEditorDialog(self, new_event)
            if dlg.exec():
                self.events.append(dlg.get_data())
                self.model.layoutChanged.emit()
                self.save_db() # Auto guardado
        else:
            QMessageBox.information(self, "Info", "Selecciona un evento para duplicar.")

    def edit(self):
        idx = self.table.selectionModel().currentIndex()
        if idx.isValid():
            dlg = EventEditorDialog(self, self.events[idx.row()])
            if dlg.exec():
                self.events[idx.row()] = dlg.get_data()
                self.model.layoutChanged.emit()
                self.save_db() # Auto guardado

    def delete(self):
        idx = self.table.selectionModel().currentIndex()
        if idx.isValid():
            if QMessageBox.question(self, "Borrar", "¿Seguro?") == QMessageBox.Yes:
                self.events.pop(idx.row())
                self.model.layoutChanged.emit()
                self.save_db() # Auto guardado

class MotorEventos:
    def __init__(self):
        self.events_cache = []
        self.last_check_second = -1
        self.load()

    def load(self):
        if os.path.exists(EVENTS_FILE):
            try:
                with open(EVENTS_FILE, 'r') as f: self.events_cache = json.load(f)
            except: self.events_cache = []
        else:
            self.events_cache = []

    def comprobar(self):
        now = datetime.now()
        if now.second == self.last_check_second: return None
        self.last_check_second = now.second
        
        # Recargar cada hora en punto por seguridad, o forzarlo desde fuera
        if now.second == 0 and now.minute == 0:
            self.load()

        curr_t = now.strftime("%H:%M:%S")
        wday = now.weekday()

        for e in self.events_cache:
            if not e.get('active', True): continue
            if not e['days'][wday]: continue

            trig = False
            if e['periodicity'] == 'once' and e['time'] == curr_t:
                trig = True
            elif e['periodicity'] == 'hourly' and e['time'][3:] == curr_t[3:]:
                trig = True
            elif e['periodicity'] == 'other' and now.hour in e.get('other_hours', []) and e['time'][3:] == curr_t[3:]:
                trig = True
            
            if trig: return e
        return None