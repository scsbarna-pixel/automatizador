using System;
using System.Collections.Generic;
using NAudio.Wave;

public class AudioEngine : IDisposable
{
    private IWavePlayer _output;
    private AudioFileReader _reader;
    private MeteringSampleProvider _meter;
    private readonly List<string> _playlist = new();
    private int _index = -1;

    public event Action<float> LevelChanged; // 0..1
    public string CurrentTrack => (_index >= 0 && _index < _playlist.Count) ? _playlist[_index] : null;

    public void SetPlaylist(List<string> accepted, int startIndex = 0)
    {
        _playlist.Clear();
        _playlist.AddRange(accepted);
        _index = Math.Clamp(startIndex, 0, _playlist.Count - 1);
    }

    public void LoadTrack(string path)
    {
        Stop();

        _reader?.Dispose();
        _reader = new AudioFileReader(path);

        // Metering sobre el audio que reproducimos (ligero)
        _meter = new MeteringSampleProvider(_reader.ToSampleProvider(), 200); // cada 200 muestras aprox.
        _meter.StreamVolume += (s, a) =>
        {
            // RMS aproximado a partir del pico por canal (simple, suficiente para VU suave)
            float peak = 0f;
            foreach (var v in a.MaxSampleValues)
                if (v > peak) peak = v;

            LevelChanged?.Invoke(peak); // 0..1
        };

        _output?.Dispose();
        _output = new WaveOutEvent(); // salida por dispositivo principal
        _output.Init(_meter);
    }

    public void Play()
    {
        if (_output == null)
        {
            // Si hay playlist y no hay cargada, carga la actual
            if (_playlist.Count > 0 && _index >= 0)
                LoadTrack(_playlist[_index]);
            else
                return;
        }
        _output.Play();
    }

    public void Stop()
    {
        _output?.Stop();
        if (_reader != null) _reader.Position = 0;
    }

    public void Cue()
    {
        // “CUE” simple: volver al inicio (puedes cambiar comportamiento si quieres)
        if (_reader != null)
            _reader.Position = 0;
    }

    public void Next()
    {
        if (_playlist.Count == 0) return;

        _index++;
        if (_index >= _playlist.Count) _index = 0;

        LoadTrack(_playlist[_index]);
        Play();
    }

    public void Dispose()
    {
        _output?.Dispose();
        _reader?.Dispose();
    }
}
