#!/usr/bin/env python3
import os
import sys
import argparse
import hashlib
import math
from collections import defaultdict
from pydub import AudioSegment

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
    """Hash raw PCM bytes for duplicate detection."""
    return hashlib.md5(audio.raw_data).hexdigest()

def analyze_directory(root_dir):
    """Walk folder, load all supported files, collect metadata + MD5."""
    meta = []
    for dirpath, _, files in os.walk(root_dir):
        for fn in files:
            if not fn.lower().endswith(SUPPORTED_EXTS):
                continue
            full = os.path.join(dirpath, fn)
            try:
                audio = AudioSegment.from_file(full)
            except Exception as e:
                print(f"⚠️  Could not open {full}: {e}", file=sys.stderr)
                continue
            meta.append({
                "path":     full,
                "duration": len(audio),
                "channels": audio.channels,
                "dBFS":     audio.dBFS,
                "md5":      compute_md5(audio),
            })
    return meta

def report_duplicates(meta):
    """Group by MD5 and report any duplicates."""
    dups = defaultdict(list)
    for m in meta:
        dups[m["md5"]].append(m["path"])
    groups = [g for g in dups.values() if len(g) > 1]
    if groups:
        print("\n?? Duplicate files detected (will skip extras):")
        for grp in groups:
            print("  - " + "\n    ".join(grp))
    return groups

def decide_target_channels(meta):
    """If any source is stereo, output in stereo; otherwise mono."""
    return 2 if any(m["channels"] > 1 for m in meta) else 1

def split_into_chunks(audio: AudioSegment):
    """Yield chunks of ≤ CHUNK_SIZE_MS each."""
    total_ms = len(audio)
    count = math.ceil(total_ms / CHUNK_SIZE_MS)
    for i in range(count):
        start = i * CHUNK_SIZE_MS
        end   = min((i+1) * CHUNK_SIZE_MS, total_ms)
        yield audio[start:end]

def process_file(info, target_ch, skip_md5, in_root, out_root):
    src = info["path"]
    # skip duplicates
    if info["md5"] in skip_md5:
        print(f"\n?? Skipping duplicate: {src}")
        return

    print(f"\n?? Processing: {src}")
    audio = AudioSegment.from_file(src)

    # 1) Channel conversion
    if audio.channels != target_ch:
        audio = audio.set_channels(target_ch)
        print(f"   • Channels: {info['channels']} → {target_ch}")

    # 2) Normalize RMS
    gain = TARGET_RMS_DBFS - audio.dBFS
    audio = audio.apply_gain(gain)
    print(f"   • Gain: {gain:+.1f} dB → new dBFS {audio.dBFS:.1f}")

    # 3) Split into ≤119 m58 s chunks
    chunks = list(split_into_chunks(audio))
    if len(chunks) > 1:
        print(f"   • Split into {len(chunks)} chunks (max {CHUNK_SIZE_MS/1000/60:.2f} min each)")

    # 4) Export chunks as 192 kbps CBR MP3
    rel = os.path.relpath(src, in_root)
    base, _ = os.path.splitext(rel)
    for idx, chunk in enumerate(chunks, start=1):
        suffix = f"_part{idx}" if len(chunks) > 1 else ""
        out_path = os.path.join(out_root, base + suffix + ".mp3")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        chunk.export(
            out_path,
            format="mp3",
            bitrate=BITRATE,
            parameters=FFMPEG_PARAMS
        )
        dur_s = len(chunk) / 1000
        print(f"   ✓ Saved: {out_path} [{int(dur_s//60):02d}:{int(dur_s%60):02d}]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Batch-fix ACX compliance for .mp3 & .wav → 192 k CBR MP3"
    )
    parser.add_argument("-i", "--input",  required=True, help="Raw files root dir")
    parser.add_argument("-o", "--output", required=True, help="Processed files root dir")
    args = parser.parse_args()

    # 1) Scan & analyze
    meta = analyze_directory(args.input)
    if not meta:
        print(f"❌ No .mp3 or .wav files found in {args.input}")
        sys.exit(1)

    # 2) Detect & report duplicates
    dup_groups = report_duplicates(meta)
    skip_md5 = set()
    for grp in dup_groups:
        # keep the first, skip the rest
        for dup_path in grp[1:]:
            h = next(m["md5"] for m in meta if m["path"] == dup_path)
            skip_md5.add(h)

    # 3) Decide mono vs. stereo
    tgt_ch = decide_target_channels(meta)
    ch_label = "stereo (2ch)" if tgt_ch == 2 else "mono (1ch)"
    print(f"\n?? Converting all files to {ch_label}")

    # 4) Process each file
    for info in meta:
        process_file(info, tgt_ch, skip_md5, args.input, args.output)

    print(f"\n✅ All done! Your ACX-compliant MP3s are in: {args.output}")
