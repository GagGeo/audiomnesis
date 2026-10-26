"""Condense long transcripts into clinical notes so prompts fit num_ctx."""
from anamnese import config
from anamnese.prompts import notes_prompt


def estimate_tokens(text: str) -> int:
    return len(text) // 3  # ~3 chars/token in French


def chunk_text(text: str, chunk_words=2200, overlap_words=200):
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        chunks.append(" ".join(words[start:start + chunk_words]))
        if start + chunk_words >= len(words):
            break
        start += chunk_words - overlap_words
    return chunks


def prepare_source(transcript: str, client, progress_cb=None, lang="fr") -> str:
    """Return the text to feed section prompts: the transcript itself when it
    fits, otherwise per-chunk clinical notes produced by the local model."""
    if estimate_tokens(transcript) <= config.CONDENSE_TOKEN_THRESHOLD:
        return transcript
    chunks = chunk_text(transcript)
    notes = []
    for i, chunk in enumerate(chunks, 1):
        if progress_cb:
            progress_cb(f"Condensation {i}/{len(chunks)}")
        notes.append(client.generate(notes_prompt(chunk, lang), num_predict=1200))
    return "\n".join(notes)
