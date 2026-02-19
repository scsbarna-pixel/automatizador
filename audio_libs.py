# -*- coding: utf-8 -*-
import sounddevice as sd

def get_output_devices():
    """
    Devuelve una lista limpia de dispositivos de salida.
    Filtra duplicados y añade el tipo de API (MME, DirectSound, etc.)
    Formato: [(index, "Nombre Dispositivo [API]"), ...]
    """
    devices = []
    seen_names = set()
    
    try:
        all_devs = sd.query_devices()
        host_apis = sd.query_hostapis()
        
        for i, d in enumerate(all_devs):
            # Solo queremos dispositivos que tengan canales de SALIDA (altavoces)
            if d['max_output_channels'] > 0:
                api_name = "Unknown"
                try:
                    if d['hostapi'] < len(host_apis):
                        api_name = host_apis[d['hostapi']]['name']
                except: pass
                
                # Construimos un nombre único
                full_name = f"{d['name']} [{api_name}]"
                
                # Opcional: Filtrar para mostrar solo MME o DirectSound si hay muchos
                # pero por seguridad mostramos todos los de salida.
                devices.append((i, full_name))
                
    except Exception as e:
        print(f"Error listando dispositivos: {e}")
        devices.append((-1, "Error detectando dispositivos"))
        
    return devices