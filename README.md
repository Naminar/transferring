
# QR File Transfer

Air-gapped, offline file transfer tool between screens and cameras using high-density animated QR code streams.

Compresses any file (documents, archives, images, binaries) using **Gzip (level 9)**, chunks it into base64 payloads with interleaving redundancy, and streams it as QR codes to be decoded by a camera in real time.

## Getting Started with `uv`

### 1. Prerequisites
Install [`uv`](https://github.com/astral-sh/uv) (fast Python package manager):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Install Project Dependencies
Clone the repository and synchronize the environment:
```bash
git clone https://github.com/Naminar/transferring.git
cd transferring
uv sync
```

---

## CLI Usage

### Option 1: Install Globally as a System CLI Command (via `uv tool`)
This installs the tool into your system `$PATH` in an isolated environment. You can then run `qr-encode` from terminal or directory without typing `uv` or activating virtual environments.

In your project root, run:
```bash
uv tool install .
```
*(Or for live editable mode while developing: `uv tool install --editable .`)*

Now you can use it directly anywhere:
```bash
qr-encode -i document.pdf -f mp4
```

> **Note:** If your terminal says `command not found: qr-encode`, make sure the `uv` tool directory is in your `PATH` by running:
> ```bash
> uv tool update-shell
> ```
> and restart your terminal.

---

### Option 2: Run via `uv run` (Without Global Install)
You can run the CLI tool directly inside the project environment:
```bash
uv run qr-encode -i /path/to/file.pdf
```
Or run interactively (it will prompt for the file path):
```bash
uv run qr-encode
```

---

### CLI Command Options

```text
Options:
  -i, --input PATH          Path to input file (required or prompted)
  -o, --output-dir PATH     Output directory (default: ./output_qr)
  -p, --prefix TEXT         Stream prefix identifier (default: FILE)
  -d, --density [450|800|1200]
                            Chunk size in bytes (default: 800)
  -r, --redundancy [1|2|3]  Redundancy repeat rounds (default: 2)
  -t, --interval FLOAT      Frame duration in seconds (default: 0.8)
  -f, --format [all|mp4|gif|png]
                            Export format (default: all)
```

### Examples:
* **Create an MP4 video for monitor playback:**
  ```bash
  qr-encode -i archive.zip -f mp4 -t 0.6
  ```
* **High density with 3× redundancy:**
  ```bash
  qr-encode -i photo.jpg -d 1200 -r 3 -o ./my_qr_export
  ```

---

### Run Localhost Server

To test the web interface locally on your computer:
```bash
uv run python -m http.server 8000
```