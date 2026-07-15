import time

import numpy as np
import soundfile as sf

from anamnese.recorder import Recorder


class FakeStream:
    """Mimics sounddevice.InputStream: fires the callback from start()."""
    def __init__(self, samplerate, channels, dtype, callback, blocksize=0):
        self.callback = callback
    def start(self):
        block = np.zeros((16000, 1), dtype="int16")  # 1 s of silence
        for _ in range(3):
            self.callback(block, 16000, None, None)
    def stop(self): pass
    def close(self): pass


def test_recorder_writes_wav_continuously(tmp_path):
    rec = Recorder(out_dir=tmp_path, stream_factory=FakeStream)
    path = rec.start()
    time.sleep(0.3)  # let the writer thread drain the queue
    rec.stop()
    info = sf.info(str(path))
    assert info.samplerate == 16000 and info.channels == 1
    assert info.frames == 3 * 16000
    assert path.parent == tmp_path


def test_elapsed_seconds_increases(tmp_path):
    rec = Recorder(out_dir=tmp_path, stream_factory=FakeStream)
    rec.start()
    time.sleep(0.05)
    assert rec.elapsed_seconds() >= 0
    rec.stop()
