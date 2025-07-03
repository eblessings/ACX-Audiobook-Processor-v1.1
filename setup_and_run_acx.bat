@echo off
title ACX Audio Fixer First-Time Setup
echo --------------------------------------------------------
echo ACX Audio Fixer - Full Setup
echo --------------------------------------------------------

:: Keep window open to show errors
echo This window will remain open — please read messages.
pause

:: Step 1 - Check for Chocolatey
where choco >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing Chocolatey...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
     "Set-ExecutionPolicy Bypass -Scope Process -Force; ^
      [System.Net.ServicePointManager]::SecurityProtocol = 3072; ^
      iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))"
    echo Chocolatey installed!
    pause
) else (
    echo Chocolatey already installed.
)

:: Step 2 - Install Python and FFmpeg
echo Installing Python and FFmpeg...
choco install -y python ffmpeg
if %errorlevel% neq 0 (
    echo Failed to install Python or FFmpeg. Please check your internet or try again.
    pause
    exit /b
)
echo Python and FFmpeg installed.
pause

:: Step 3 - Install pip dependencies
echo Installing Python packages...
pip install --upgrade pip
pip install pydub
pause

:: Step 4 - Setup directories
mkdir C:\ACXFixer\raw
mkdir C:\ACXFixer\processed

:: Step 5 - Write Python script to file
echo Creating Python script...
(
echo import os, sys, argparse, hashlib
echo from collections import defaultdict
echo from pydub import AudioSegment
echo TARGET_RMS_DBFS = -20.0
echo MAX_DURATION_MS = 120 * 60 * 1000
echo BITRATE = "192k"
echo FFMPEG_PARAMS = ["-acodec", "libmp3lame", "-b:a", BITRATE, "-write_xing", "0"]
echo def compute_md5(audio): return hashlib.md5(audio.raw_data).hexdigest()
echo def analyze_directory(root_dir):
echo ^    meta = []
echo ^    for dirpath, _, files in os.walk(root_dir):
echo ^        for f in files:
echo ^            if not f.lower().endswith(".mp3"): continue
echo ^            full = os.path.join(dirpath, f)
echo ^            try: audio = AudioSegment.from_file(full, "mp3")
echo ^            except: continue
echo ^            meta.append({ "path": full, "duration_ms": len(audio), "channels": audio.channels, "dBFS": audio.dBFS, "md5": compute_md5(audio) })
echo ^    return meta
echo def report_duplicates(meta):
echo ^    dups = defaultdict(list)
echo ^    for m in meta: dups[m["md5"]].append(m["path"])
echo ^    return [paths for paths in dups.values() if len(paths) > 1]
echo def decide_channels(meta): return 2 if any(m["channels"] > 1 for m in meta) else 1
echo def process_file(m, target_channels, out_root, skip_hashes):
echo ^    audio = AudioSegment.from_file(m["path"], "mp3")
echo ^    if m["md5"] in skip_hashes: return
echo ^    if audio.channels != target_channels: audio = audio.set_channels(target_channels)
echo ^    gain = TARGET_RMS_DBFS - audio.dBFS
echo ^    audio = audio.apply_gain(gain)
echo ^    segments = [audio[i:i+MAX_DURATION_MS] for i in range(0, len(audio), MAX_DURATION_MS)]
echo ^    base = os.path.splitext(os.path.relpath(m["path"], args.input))[0]
echo ^    for idx, seg in enumerate(segments, 1):
echo ^        suffix = f"_part{idx}" if len(segments) > 1 else ""
echo ^        out_path = os.path.join(out_root, base + suffix + ".mp3")
echo ^        os.makedirs(os.path.dirname(out_path), exist_ok=True)
echo ^        seg.export(out_path, format="mp3", bitrate=BITRATE, parameters=FFMPEG_PARAMS)
echo if __name__ == "__main__":
echo ^    parser = argparse.ArgumentParser()
echo ^    parser.add_argument("--input", "-i", required=True)
echo ^    parser.add_argument("--output", "-o", required=True)
echo ^    args = parser.parse_args()
echo ^    meta = analyze_directory(args.input)
echo ^    dups = report_duplicates(meta)
echo ^    skip = set()
echo ^    for grp in dups:
echo ^        for p in grp[1:]: h = next(m["md5"] for m in meta if m["path"] == p); skip.add(h)
echo ^    ch = decide_channels(meta)
echo ^    for m in meta: process_file(m, ch, args.output, skip)
echo ^    print("\nDone.")
) > C:\ACXFixer\batch_acx_fix.py
echo Python script saved.

:: Step 6 - Prompt user to add MP3s
echo --------------------------------------------------------
echo ✅ Setup complete!
echo Now copy your .mp3 files into:
echo     C:\ACXFixer\raw
echo Then press any key to continue.
pause

:: Step 7 - Run fixer
cd /d C:\ACXFixer
python batch_acx_fix.py --input raw --output processed

pause