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
MAX_DURATION_MS = 120 * 60 * 1000   # 120 minutes in milliseconds
BITRATE        = "192k"
FFMPEG_PARAMS  = ["-acodec", "libmp3lame", "-b:a", BITRATE, "-write_xing", "0"]
SUPPORTED_EXTS = (".mp3", ".wav")
# ────────────────────────────────────────────────────────────────────────────────

def compute_md5(audio: AudioSegment) -> str:
    """Hash the raw PCM bytes to detect duplicates."""
    return hashlib.md5(audio.raw_data).hexdigest()

def analyze_directory(root_dir):
    """Walk folder, load every supported file, collect metadata and MD5."""
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
                "path":       full,
                "duration":   len(audio),
                "channels":   audio.channels,
                "dBFS":       audio.dBFS,
                "md5":        compute_md5(audio),
            })
    return meta

def report_duplicates(meta):
    """Group by MD5 and report any duplicates."""
    dups = defaultdict(list)
    for m in meta:
        dups[m["md5"]].append(m["path"])
    groups = [grp for grp in dups.values() if len(grp) > 1]
    if groups:
        print("\n?? Duplicate files detected (skipping duplicates):")
        for grp in groups:
            print("  - " + "\n    ".join(grp))
    return groups

def decide_target_channels(meta):
    """If any source is stereo, use stereo; otherwise mono."""
    return 2 if any(m["channels"] > 1 for m in meta) else 1

def split_into_chunks(audio: AudioSegment):
    """Yield segments all ≤ MAX_DURATION_MS."""
    total_ms = len(audio)
    parts = math.ceil(total_ms / MAX_DURATION_MS)
    for i in range(parts):
        start = i * MAX_DURATION_MS
        end   = min((i+1) * MAX_DURATION_MS, total_ms)
        yield audio[start:end]

def process_file(info, target_ch, skip_md5, input_root, output_root):
    src = info["path"]
    print(f"\n?? Processing: {src}")
    # skip exact duplicates
    if info["md5"] in skip_md5:
        print("   • Duplicate → skipped")
        return

    audio = AudioSegment.from_file(src)

    # 1) Channel conversion
    if audio.channels != target_ch:
        audio = audio.set_channels(target_ch)
        print(f"   • Channels: {info['channels']}→{target_ch}")

    # 2) RMS normalize
    gain = TARGET_RMS_DBFS - audio.dBFS
    audio = audio.apply_gain(gain)
    print(f"   • Gain applied: {gain:+.1f} dB → new dBFS {audio.dBFS:.1f}")

    # 3) Split if needed
    chunks = list(split_into_chunks(audio))
    if len(chunks) > 1:
        print(f"   • Split into {len(chunks)} parts (≤120 min each)")

    # 4) Export each chunk
    rel = os.path.relpath(src, input_root)
    base, _ = os.path.splitext(rel)
    for idx, chunk in enumerate(chunks, start=1):
        suffix = f"_part{idx}" if len(chunks) > 1 else ""
        out_path = os.path.join(output_root, base + suffix + ".mp3")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        chunk.export(
            out_path,
            format="mp3",
            bitrate=BITRATE,
            parameters=FFMPEG_PARAMS
        )
        dur = len(chunk) / 1000
        print(f"   ✓ Saved: {out_path}  [{int(dur//60):02d}:{int(dur%60):02d}]")

if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Batch-fix ACX compliance for .mp3 & .wav → 192k CBR MP3"
    )
    p.add_argument("-i", "--input",  required=True, help="Raw files root dir")
    p.add_argument("-o", "--output", required=True, help="Processed files root dir")
    args = p.parse_args()

    meta = analyze_directory(args.input)
    if not meta:
        print("❌ No .mp3 or .wav files found in", args.input)
        sys.exit(1)

    # 1) Report & skip duplicates
    dup_groups = report_duplicates(meta)
    skip_md5 = set()
    for grp in dup_groups:
        # keep first, skip the rest
        for dup_path in grp[1:]:
            h = next(m["md5"] for m in meta if m["path"] == dup_path)
            skip_md5.add(h)

    # 2) Decide mono vs. stereo
    tgt_ch = decide_target_channels(meta)
    ch_label = "stereo (2ch)" if tgt_ch == 2 else "mono (1ch)"
    print(f"\n?? Will convert all files to {ch_label}")

    # 3) Process
    for info in meta:
        process_file(info, tgt_ch, skip_md5, args.input, args.output)

    print("\n✅ All done! Your ACX-compliant MP3s live in:", args.output)
