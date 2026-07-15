import shutil
from pathlib import Path
from unittest import mock

import pytest

from anamnese import config
from anamnese.transcriber import build_command, transcribe, to_whisper_wav


def test_build_command_french_txt_output(tmp_path):
    cmd = build_command(tmp_path / "a.wav", tmp_path / "out")
    s = " ".join(str(c) for c in cmd)
    assert config.WHISPER_BIN in s and "-l fr" in s and "--output-txt" in s
    assert str(config.WHISPER_MODEL) in s


def test_transcribe_reads_txt_output(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"fake")
    def fake_run(cmd, **kw):
        # whisper-cli writes <output-file>.txt
        out_base = cmd[cmd.index("--output-file") + 1]
        Path(str(out_base) + ".txt").write_text("Bonjour docteur.\n")
        return mock.MagicMock(returncode=0, stderr=b"")
    with mock.patch("anamnese.transcriber.subprocess.run", fake_run):
        assert transcribe(wav) == "Bonjour docteur."


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")
def test_to_whisper_wav_converts_to_16k_mono(tmp_path):
    import soundfile as sf
    import numpy as np
    src = tmp_path / "in.wav"
    sf.write(src, np.zeros(44100, dtype="int16"), 44100)  # 1 s at 44.1 kHz
    out = to_whisper_wav(src, tmp_path)
    info = sf.info(str(out))
    assert info.samplerate == 16000 and info.channels == 1


@pytest.mark.skipif(shutil.which(config.WHISPER_BIN) is None
                    or not config.WHISPER_MODEL.exists(),
                    reason="whisper-cli + model required (installed by install.sh)")
def test_real_transcription_of_synthesized_french(tmp_path):
    import subprocess
    aiff = tmp_path / "t.aiff"
    subprocess.run(["say", "-v", "Thomas",
                    "Bonjour, je viens consulter pour des troubles de la mémoire.",
                    "-o", str(aiff)], check=True)
    wav = to_whisper_wav(aiff, tmp_path)
    text = transcribe(wav).lower()
    assert "mémoire" in text
