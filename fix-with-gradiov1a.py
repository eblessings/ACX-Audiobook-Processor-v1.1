#!/usr/bin/env python3
import os
import math
import tempfile
import zipfile
from pydub import AudioSegment
import gradio as gr

# ─── CONFIG ────────────────────────────────────────────────────────────────
TARGET_RMS_DBFS = -20.0
MAX_DURATION_MS = 120 * 60 * 1000           # 120 minutes in ms
MARGIN_MS       = 2 * 1000                  # subtract 2 seconds
CHUNK_SIZE_MS   = MAX_DURATION_MS - MARGIN_MS
BITRATE         = "192k"
FFMPEG_PARAMS   = ["-acodec", "libmp3lame", "-b:a", BITRATE, "-write_xing", "0"]
SUPPORTED_EXTS  = (".mp3", ".wav")
# ───────────────────────────────────────────────────────────────────────────

def split_into_chunks(audio: AudioSegment):
    total_ms = len(audio)
    parts = math.ceil(total_ms / CHUNK_SIZE_MS)
    for i in range(parts):
        start = i * CHUNK_SIZE_MS
        end   = min((i + 1) * CHUNK_SIZE_MS, total_ms)
        yield audio[start:end]

def process_audio(file_path):
    """
    - Loads the uploaded file
    - Normalizes to TARGET_RMS_DBFS
    - Splits into ≤119m58s chunks
    - Exports as 192 kbps CBR MP3
    - Zips all output files and returns the .zip path
    """
    # 1) Prepare working dirs
    work_out = tempfile.mkdtemp(prefix="acx_out_")
    zip_out  = os.path.join(tempfile.mkdtemp(prefix="acx_zip_"), "processed_audio.zip")

    # 2) Load audio
    audio = AudioSegment.from_file(file_path)

    # 3) Normalize RMS
    gain = TARGET_RMS_DBFS - audio.dBFS
    audio = audio.apply_gain(gain)

    # 4) Split into chunks
    chunks = list(split_into_chunks(audio))

    # 5) Export each chunk
    base = os.path.splitext(os.path.basename(file_path))[0]
    for idx, chunk in enumerate(chunks, start=1):
        suffix = f"_part{idx}" if len(chunks) > 1 else ""
        out_name = f"{base}{suffix}.mp3"
        out_path = os.path.join(work_out, out_name)
        chunk.export(
            out_path,
            format="mp3",
            bitrate=BITRATE,
            parameters=FFMPEG_PARAMS
        )

    # 6) Zip the results
    with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED) as zf:
        for fn in sorted(os.listdir(work_out)):
            zf.write(os.path.join(work_out, fn), arcname=fn)

    return zip_out

# ─── Gradio UI ───────────────────────────────────────────────────────────────
iface = gr.Interface(
    fn=process_audio,
    inputs=gr.File(label="Upload MP3 or WAV", file_types=list(SUPPORTED_EXTS)),
    outputs=gr.File(label="Download Processed ZIP"),
    title="ACX Audio Compliance Fixer",
    description=(
        "Uploads a WAV/MP3, normalizes to –20 dB RMS, encodes at 192 kbps CBR, "
        "splits into ≤119 m 58 s parts, and returns a ZIP of the MP3s."
    ),
    allow_flagging="never",
    share=True,
)

if __name__ == "__main__":
    iface.launch()
