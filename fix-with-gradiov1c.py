#!/usr/bin/env python3
import os
import io
import math
import hashlib
import tempfile
import zipfile
from typing import List
from pydub import AudioSegment
import gradio as gr

# ─── CONFIG ─────────────────────────────────────────────────────────────────────
TARGET_RMS_DBFS = -20.0
MAX_DURATION_MS = 120 * 60 * 1000         # 120 minutes in ms
MARGIN_MS       = 2 * 1000                # subtract 2 seconds (2000 ms)
CHUNK_MS        = MAX_DURATION_MS - MARGIN_MS
BITRATE         = "192k"
FFMPEG_PARAMS   = ["-acodec", "libmp3lame", "-b:a", BITRATE, "-write_xing", "0"]
SUPPORTED_EXTS  = (".mp3", ".wav")
# ────────────────────────────────────────────────────────────────────────────────

def split_chunks(audio: AudioSegment):
    total_ms = len(audio)
    parts = math.ceil(total_ms / CHUNK_MS)
    for i in range(parts):
        start = i * CHUNK_MS
        end   = min((i+1)*CHUNK_MS, total_ms)
        yield audio[start:end]

def process_files(file_paths: List[str]) -> str:
    """
    Takes a list of local filepaths (mp3/wav), processes them,
    and returns the path to a ZIP containing all output MP3s.
    """
    work_dir = tempfile.mkdtemp(prefix="acx_proc_")
    zip_path = os.path.join(work_dir, "acx_processed.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in file_paths:
            ext = os.path.splitext(path)[1].lower()
            if ext not in SUPPORTED_EXTS:
                continue
            audio = AudioSegment.from_file(path)
            # Normalize RMS
            gain = TARGET_RMS_DBFS - audio.dBFS
            audio = audio.apply_gain(gain)
            # Split into ≤ 119m58s chunks
            chunks = list(split_chunks(audio))
            base = os.path.splitext(os.path.basename(path))[0]
            for idx, chunk in enumerate(chunks, start=1):
                suffix = f"_part{idx}" if len(chunks)>1 else ""
                out_name = f"{base}{suffix}.mp3"
                out_path = os.path.join(work_dir, out_name)
                chunk.export(
                    out_path,
                    format="mp3",
                    bitrate=BITRATE,
                    parameters=FFMPEG_PARAMS
                )
                zf.write(out_path, arcname=out_name)
    return zip_path

# ─── GRADIO UI ──────────────────────────────────────────────────────────────────
with gr.Blocks() as demo:
    gr.Markdown("## ACX-Compliance Audio Processor For Kassam Bhai")
    gr.Markdown(
        "- **Upload**: .mp3 or .wav (multiple allowed)\n"
        "- **Process**: Normalize to –20 dB RMS, 192 kbps CBR, split ≤119 m 58 s\n"
        "- **Download**: Single ZIP archive"
    )
    file_input = gr.File(
        label="Upload your MP3/WAV files",
        file_count="multiple",
        type="filepath"               # <— use filepath, not 'file'
    )
    process_btn = gr.Button("Process Files")
    output_zip = gr.File(
        label="Download Processed ZIP",
        type="filepath"               # <— return a filepath string
    )
    process_btn.click(
        fn=process_files,
        inputs=file_input,
        outputs=output_zip
    )
    gr.Markdown("Made with ❤️ for ACX compliance.")

if __name__ == "__main__":
    # host on all interfaces, port 7654, and also get a Gradio share link (expires in 1 week)
    launch_result = demo.launch(
        server_name="0.0.0.0",
        server_port=7654,
        share=True,
        inbrowser=False
    )

    # demo.launch returns a tuple (local_url, share_url) when share=True
    try:
        local_url, share_url = launch_result
    except (TypeError, ValueError):
        # fallback if it only returns a single string
        local_url = launch_result
        share_url = None

    print(f"\n??  App is running on your server at: {local_url}")
    if share_url:
        print(f"??  Public share link (expires in 1 week): {share_url}\n")
    else:
        print("\n(No public share link was created.)\n")
