
# ACX Audio Processor v1.1

Batch-fix your audiobook files to ACX compliance, converting `.mp3` & `.wav` sources into 192 kbps constant-bitrate MP3s with normalized RMS, stereo/mono conversion, duplicate removal, chunk splitting, and more.

## Features

- **RMS Normalization**  
  Adjusts audio to a target RMS of −20 dBFS for consistent loudness.

- **Duplicate Detection**  
  MD5-hash-based duplicate skipping.

- **Channel Conversion**  
  Converts all sources to mono (1 ch) or stereo (2 ch) based on input.

- **Chunk Splitting**  
  Splits any track longer than 119 minutes 58 seconds into smaller parts.

- **192 kbps CBR MP3 Export**  
  Uses LAME (`libmp3lame`) at 192 kbps for ACX-compliant files.

- **Gradio GUI**  
  Launch a local web interface for point-and-click processing.

---

## Prerequisites

- **Python 3.8+**  
- **FFmpeg CLI** installed and in your `PATH`  
  ```bash
  # Ubuntu/Debian
  sudo apt update && sudo apt install ffmpeg

  # macOS (Homebrew)
  brew install ffmpeg

Git (to clone the repo)



---

Installation

1. Clone this repository:

git clone https://github.com/eblessings/ACX-Audiobook-Processor-v1.1.git
cd ACX-Audiobook-Processor-v1.1


2. Create & activate a Python virtual environment:

python3 -m venv venv
source venv/bin/activate


3. Install Python dependencies:

pip install --upgrade pip
pip install -r requirements.txt




---

Getting Started

1. Command-Line Interface (CLI)

Process an entire folder of raw .mp3/.wav files:

# Basic usage:
python3 fix-with-gradiov1c.py \
  --input  /path/to/raw_audio/ \
  --output /path/to/processed_audio/

--input (-i): Root directory containing your source audio.

--output (-o): Destination directory for ACX-compliant MP3s.


The script will:

1. Scan and analyze all .mp3/.wav files.


2. Report & skip MD5 duplicates.


3. Determine whether to output mono or stereo.


4. Normalize loudness, split long tracks, and export 192 kbps MP3s.



2. Gradio Web Interface

A simple GUI lets you point to input/output folders without the CLI.

1. Run the Gradio app:

python3 gradio_app.py


2. Open your browser at the address printed (e.g. http://127.0.0.1:7860).


3. Select your input/output folders and click “Process”.




---

Configuration

You can tweak constants at the top of fix-with-gradiov1c.py:

# ─── CONFIG ────────────────────────────────────────────────
TARGET_RMS_DBFS = -20.0       # loudness target in dBFS
MAX_DURATION_MS = 120*60*1000 # max chunk size
CHUNK_SIZE_MS = MAX_DURATION_MS - 2000
BITRATE       = "192k"        # export bitrate
SUPPORTED_EXTS = (".mp3", ".wav")
# ──────────────────────────────────────────────────────────


---

Development & Contributing

1. Fork the repo


2. Create a feature branch (git checkout -b feat/new-feature)


3. Commit your changes (git commit -m "Add feature")


4. Push to your branch (git push origin feat/new-feature)


5. Open a Pull Request



Please adhere to PEP 8 style, include tests/examples, and update this README as needed.


---

License

MIT © eBlessings

---

### requirements.txt

```text
gradio>=3.0
pydub>=0.25.1

> Note:

pydub relies on the external ffmpeg binary—ensure it’s installed.

All other imports (argparse, hashlib, math, collections) are part of the Python standard library.




