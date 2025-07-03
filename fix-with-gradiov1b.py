#!/usr/bin/env python3
import os
import io
import math
import hashlib
import tempfile
import zipfile
import argparse
from pydub import AudioSegment
import gradio as gr

# ─── CONFIG ─────────────────────────────────────────────────────────────────────
TARGET_RMS_DBFS = -20.0
MAX_DURATION_MS = 120 * 60 * 1000           # 120 minutes in ms
MARGIN_MS       = 2 * 1000                  # subtract 2 seconds = 2000 ms
CHUNK_SIZE_MS   = MAX_DURATION_MS - MARGIN_MS
BITRATE         = "192k"
FFMPEG_PARAMS   = ["-acodec", "libmp3lame", "-b:a", BITRATE, "-write_xing", "0"]
SUPPORTED_EXTS  = (".mp3", ".wav")
# ────────────────────────────────────────────────────────────────────────────────

def compute_md5(audio: AudioSegment) -> str:
    return hashlib.md5(audio.raw_data).hexdigest()

def split_into_chunks(audio: AudioSegment):
    total_ms = len(audio)
    count = math.ceil(total_ms / CHUNK_SIZE_MS)
    for i in range(count):
        start = i * CHUNK_SIZE_MS
        end   = min((i+1) * CHUNK_SIZE_MS, total_ms)
        yield audio[start:end]

def process_files(uploaded_files):
    """
    uploaded_files: list of file-like objects from Gradio (each has .name and .file path)
    Returns: path to a ZIP file containing all processed MP3s
    """
    # Create a temp dir for processing
    work_dir = tempfile.mkdtemp(prefix="acx_proc_")
    zip_path = os.path.join(work_dir, "acx_processed.zip")
    zipf = zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED)

    for up in uploaded_files:
        # Only process supported extensions
        ext = os.path.splitext(up.name)[1].lower()
        if ext not in SUPPORTED_EXTS:
            continue

        # Load audio
        audio = AudioSegment.from_file(up.name)
        original_name = os.path.splitext(os.path.basename(up.name))[0]

        # Normalize RMS
        gain = TARGET_RMS_DBFS - audio.dBFS
        audio = audio.apply_gain(gain)

        # Split into chunks ≤119m58s
        chunks = list(split_into_chunks(audio))

        # Export each chunk
        for idx, chunk in enumerate(chunks, start=1):
            suffix = "" if len(chunks)==1 else f"_part{idx}"
            out_name = f"{original_name}{suffix}.mp3"
            out_path = os.path.join(work_dir, out_name)
            chunk.export(
                out_path,
                format="mp3",
                bitrate=BITRATE,
                parameters=FFMPEG_PARAMS
            )
            zipf.write(out_path, arcname=out_name)

    zipf.close()
    return zip_path

# ─── GRADIO UI ──────────────────────────────────────────────────────────────────
with gr.Blocks() as demo:
    gr.Markdown("## ACX-Compliance Audio Processor")
    gr.Markdown(
        "- **Uploads**: .mp3 or .wav (multiple files allowed)\n"
        "- **Outputs**: 192 kbps CBR MP3, normalized to –20 dB RMS, split into ≤ 119 min 58 s\n"
        "- **Download**: Single ZIP of all processed files"
    )
    file_input = gr.File(
        label="Upload your MP3/WAV files",
        file_count="multiple",
        type="file",
        file_types=[".mp3", ".wav"]
    )
    process_btn = gr.Button("Process Files")
    output_zip = gr.File(label="Download Processed ZIP")
    process_btn.click(
        fn=process_files,
        inputs=file_input,
        outputs=output_zip
    )
    gr.Markdown("Made with ❤️ for ACX compliance.")

if __name__ == "__main__":
    demo.launch(share=True)
