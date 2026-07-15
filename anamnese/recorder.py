"""Crash-safe microphone recorder: audio hits the disk continuously."""
import datetime
import queue
import threading
import time
from pathlib import Path

import numpy as np
import soundfile as sf

from anamnese import config


def _default_stream_factory(samplerate, channels, dtype, callback, blocksize=0):
    import sounddevice as sd  # imported lazily: not needed for file-based flows
    return sd.InputStream(samplerate=samplerate, channels=channels,
                          dtype=dtype, callback=callback, blocksize=blocksize)


class Recorder:
    def __init__(self, out_dir=config.RECORDINGS_DIR,
                 stream_factory=_default_stream_factory):
        self.out_dir = Path(out_dir)
        self._factory = stream_factory
        self._queue = queue.Queue()
        self._stream = None
        self._writer = None
        self._stop_flag = threading.Event()
        self._started_at = None
        self.path = None

    def start(self) -> Path:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.path = self.out_dir / f"enregistrement_{stamp}.wav"
        self._stop_flag.clear()
        self._writer = threading.Thread(target=self._write_loop, daemon=True)
        self._writer.start()
        self._stream = self._factory(
            samplerate=config.SAMPLE_RATE, channels=config.CHANNELS,
            dtype="int16", callback=self._callback)
        self._stream.start()
        self._started_at = time.monotonic()
        return self.path

    def _callback(self, indata, frames, time_info, status):
        self._queue.put(bytes(indata))  # copy: PortAudio reuses the buffer

    def _write_loop(self):
        with sf.SoundFile(str(self.path), mode="w",
                          samplerate=config.SAMPLE_RATE,
                          channels=config.CHANNELS, subtype="PCM_16") as f:
            while not (self._stop_flag.is_set() and self._queue.empty()):
                try:
                    data = self._queue.get(timeout=0.2)
                except queue.Empty:
                    continue
                f.write(np.frombuffer(data, dtype="int16").reshape(-1, 1))
                f.flush()  # crash-safe: data lands on disk as we go

    def elapsed_seconds(self) -> int:
        return int(time.monotonic() - self._started_at) if self._started_at else 0

    def stop(self) -> Path:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._stop_flag.set()
        if self._writer is not None:
            self._writer.join(timeout=10)
        return self.path
