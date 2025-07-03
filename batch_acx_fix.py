#!/usr/bin/env python3
import os
import sys
import argparse
import hashlib
from collections import defaultdict
from pydub import AudioSegment

# === CONFIGURATION ===
TARGET_RMS_DBFS    = -20.0
MAX_DURATION_MS    = 120 * 60 * 1000   # 120 minutes in ms
BITRATE            = "192k"
FFMPEG_PARAMS      = ["-acodec", "libmp3lame", "-b:a", BITRATE, "-write_xing", "0"]


def compute_md5(audio: AudioSegment) -> str:
    """Hash the raw PCM bytes to detect duplicates."""
    return hashlib.md5(audio.raw_data).hexdigest()


def analyze_directory(root_dir):
    """Load every MP3, collect metadata and group duplicates."""
    meta = []
    for dirpath, _, files in os.walk(root_dir):
        for f in files:
            if not f.lower().endswith(".mp3"):
                continue
            full = os.path.join(dirpath, f)
            try:
                audio = AudioSegment.from_file(full, "mp3")
            except Exception as e:
                print(f"⚠️  Could not open {full!r}: {e}", file=sys.stderr)
                continue
            meta.append({
                "path": full,
                "duration_ms": len(audio),
                "channels": audio.channels,
                "dBFS": audio.dBFS,
                "md5": compute_md5(audio),
            })
    return meta


def report_duplicates(meta):
    dups = defaultdict(list)
    for m in meta:
        dups[m["md5"]].append(m["path"])
    groups = [paths for paths in dups.values() if len(paths) > 1]
    if groups:
        print("\n??  Duplicate files detected:")
        for grp in groups:
            print("  - " + "\n    ".join(grp))
    return groups


def decide_channels(meta):
    """If any file is stereo, output should be stereo; else mono."""
    return 2 if any(m["channels"] > 1 for m in meta) else 1


def process_file(m, target_channels, out_root, skip_hashes):
    src = m["path"]
    print(f"\n?? Processing: {src}")
    audio = AudioSegment.from_file(src, "mp3")

    # --- skip duplicates ---
    if m["md5"] in skip_hashes:
        print("   • Skipping duplicate.")
        return

    # --- channel conversion ---
    if audio.channels != target_channels:
        audio = audio.set_channels(target_channels)
        print(f"   • Channels: {m['channels']} → {target_channels}")

    # --- normalize RMS ---
    gain = TARGET_RMS_DBFS - audio.dBFS
    audio = audio.apply_gain(gain)
    print(f"   • Applied gain: {gain:+.1f} dB  (new dBFS: {audio.dBFS:.1f})")

    # --- splitting if needed ---
    segments = []
    if len(audio) > MAX_DURATION_MS:
        print("   • Too long → splitting into ≤120 min segments")
        for i in range(0, len(audio), MAX_DURATION_MS):
            segments.append(audio[i : i + MAX_DURATION_MS])
    else:
        segments = [audio]

    # --- export each segment ---
    rel_path = os.path.relpath(src, args.input)
    base, _ = os.path.splitext(rel_path)
    for idx, seg in enumerate(segments, 1):
        suffix = f"_part{idx}" if len(segments) > 1 else ""
        out_path = os.path.join(out_root, base + suffix + ".mp3")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        seg.export(out_path, format="mp3", bitrate=BITRATE, parameters=FFMPEG_PARAMS)
        print(f"   ✓ Saved: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch-fix ACX compliance for MP3s")
    parser.add_argument("--input",  "-i", required=True, help="Directory of raw MP3s")
    parser.add_argument("--output", "-o", required=True, help="Directory for processed MP3s")
    args = parser.parse_args()

    # 1) Scan & analyze
    metadata = analyze_directory(args.input)
    if not metadata:
        print("No MP3 files found in", args.input)
        sys.exit(1)

    # 2) Report duplicates
    dup_groups = report_duplicates(metadata)
    # flatten all duplicate hashes except the first in each group
    skip = set()
    for grp in dup_groups:
        # We'll keep grp[0], skip the rest
        for p in grp[1:]:
            # find its hash
            h = next(m["md5"] for m in metadata if m["path"] == p)
            skip.add(h)

    # 3) Decide target channels
    tgt_ch = decide_channels(metadata)
    print(f"\n?? Converting all files to {'stereo (2ch)' if tgt_ch==2 else 'mono (1ch)'}")

    # 4) Process each unique file
    for m in metadata:
        process_file(m, tgt_ch, args.output, skip)

    print("\n✅ All done. Check above for any warnings or duplicates.")
