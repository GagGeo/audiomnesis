"""Transcription via whisper.cpp (whisper-cli subprocess, exits when done)."""
import subprocess
import tempfile
from pathlib import Path

from anamnese import config


class TranscriptionError(RuntimeError):
    pass


def to_whisper_wav(audio_path: Path, workdir: Path) -> Path:
    """Convert any audio file to 16 kHz mono 16-bit WAV via ffmpeg."""
    out = Path(workdir) / (Path(audio_path).stem + "_16k.wav")
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", str(audio_path),
         "-ar", str(config.SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le",
         str(out)],
        capture_output=True)
    if r.returncode != 0:
        raise TranscriptionError(
            f"Conversion audio échouée : {r.stderr.decode(errors='replace')[-400:]}")
    return out


def build_command(wav_path: Path, output_base: Path) -> list:
    return [config.WHISPER_BIN,
            "-m", str(config.WHISPER_MODEL),
            "-l", "fr",
            "-f", str(wav_path),
            "--output-txt",
            "--output-file", str(output_base),
            "--no-timestamps"]


def transcribe(wav_path: Path) -> str:
    """Run whisper-cli on a 16 kHz mono WAV; return the transcript text."""
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "transcript"
        r = subprocess.run(build_command(wav_path, base), capture_output=True)
        if r.returncode != 0:
            raise TranscriptionError(
                f"whisper-cli a échoué : {r.stderr.decode(errors='replace')[-400:]}")
        txt = Path(str(base) + ".txt")
        if not txt.exists():
            raise TranscriptionError("whisper-cli n'a pas produit de fichier texte.")
        return txt.read_text(encoding="utf-8").strip()
