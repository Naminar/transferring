#!/usr/bin/env python3
import os
import sys
import gzip
import base64
import argparse
import urllib.parse
from pathlib import Path

try:
    import qrcode
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: Missing libraries. Install them.")
    print("Use uv sync")
    sys.exit(1)

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


def encode_file_to_chunks(file_path: str, chunk_size: int = 800) -> tuple[str, str, list[str]]:
    """Compresses file using gzip (level 9) and encodes to base64 chunks."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    filename = path.name
    encoded_filename = urllib.parse.quote(filename, safe='')

    with open(path, 'rb') as f:
        raw_data = f.read()

    compressed_data = gzip.compress(raw_data, compresslevel=9)
    b64_content = base64.b64encode(compressed_data).decode('ascii')

    # Split into chunks
    chunks = [b64_content[i:i + chunk_size] for i in range(0, len(b64_content), chunk_size)]
    
    orig_kb = len(raw_data) / 1024
    comp_kb = len(compressed_data) / 1024
    ratio = (len(compressed_data) / len(raw_data)) * 100 if len(raw_data) > 0 else 100

    print(f"\nFile: {filename}")
    print(f"   Original: {orig_kb:.1f} KB -> Compressed: {comp_kb:.1f} KB ({ratio:.0f}%)")
    print(f"   Total Chunks: {len(chunks)} (Chunk size: {chunk_size} bytes)")

    return filename, encoded_filename, chunks


def build_frames(prefix: str, encoded_filename: str, chunks: list[str], redundancy: int = 2) -> list[tuple[int, int, str]]:
    """Builds interleaved frame payloads matching generator.html logic."""
    total = len(chunks)
    frames = []

    for rnd in range(redundancy):
        for pos in range(total):
            idx = ((pos + rnd) % total) + 1
            payload = f"{prefix}|{encoded_filename}|{idx}/{total}|{chunks[idx - 1]}"
            frames.append((idx, total, payload))

    return frames


def generate_qr_image(payload: str, img_size: int = 500, label_text: str = "") -> Image.Image:
    """Generates a QR Code PIL Image with low error correction (EC-L)."""
    qr = qrcode.QRCode(
        version=None, # Auto-detect version
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    qr_img = qr_img.resize((img_size, img_size), Image.NEAREST)

    if label_text:
        # Create a container with space for bottom label
        canvas_h = img_size + 40
        canvas = Image.new('RGB', (img_size, canvas_h), color=(255, 255, 255))
        canvas.paste(qr_img, (0, 0))
        
        draw = ImageDraw.Draw(canvas)
        draw.text((img_size // 2, img_size + 12), label_text, fill=(80, 80, 80), anchor="mm")
        return canvas

    return qr_img


def main():
    parser = argparse.ArgumentParser(description="Encode any file into animated QR codes for scanner.html")
    parser.add_argument("-i", "--input", help="Path to input file")
    parser.add_argument("-o", "--output-dir", default="./output_qr", help="Output directory (default: ./output_qr)")
    parser.add_argument("-p", "--prefix", default="FILE", help="Stream prefix (default: FILE)")
    parser.add_argument("-d", "--density", type=int, default=800, choices=[450, 800, 1200], help="Chunk size in bytes (default: 800)")
    parser.add_argument("-r", "--redundancy", type=int, default=2, choices=[1, 2, 3], help="Redundancy repeats (default: 2)")
    parser.add_argument("-t", "--interval", type=float, default=0.8, help="Frame duration in seconds (default: 0.8)")
    parser.add_argument("-f", "--format", default="all", choices=["all", "mp4", "gif", "png"], help="Output format (default: all)")

    args = parser.parse_args()

    # Interactive input if run without arguments
    file_path = args.input
    if not file_path:
        file_path = input("Enter path to file: ").strip().strip('"').strip("'")

    if not os.path.exists(file_path):
        print(f"❌ File does not exist: {file_path}")
        return

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Compress & Slice
    filename, enc_name, chunks = encode_file_to_chunks(file_path, chunk_size=args.density)
    frames_meta = build_frames(args.prefix, enc_name, chunks, redundancy=args.redundancy)
    total_frames = len(frames_meta)

    print(f"Generating {total_frames} QR frames...")

    # 2. Render PIL Images
    images = []
    png_folder = output_dir / f"{Path(filename).stem}_png"
    if args.format in ["all", "png"]:
        png_folder.mkdir(parents=True, exist_ok=True)

    for i, (idx, total, payload) in enumerate(frames_meta):
        label = f"Frame {i + 1}/{total_frames} (Chunk #{idx}/{total})"
        img = generate_qr_image(payload, img_size=500, label_text=label)
        images.append(img)

        if args.format in ["all", "png"]:
            img.save(png_folder / f"frame_{i + 1:03d}_chunk_{idx:03d}.png")
        
        # Progress indicator
        sys.stdout.write(f"\r   Rendering: {i + 1}/{total_frames} frames")
        sys.stdout.flush()

    print("\n   Rendering complete!")

    # 3. Export Formats
    stem = Path(filename).stem

    # A. Animated GIF
    if args.format in ["all", "gif"]:
        gif_path = output_dir / f"{stem}_stream.gif"
        images[0].save(
            gif_path,
            save_all=True,
            append_images=images[1:],
            duration=int(args.interval * 1000),
            loop=0
        )
        print(f"GIF saved: {gif_path}")

    # B. MP4 Video (OpenCV)
    if args.format in ["all", "mp4"]:
        if OPENCV_AVAILABLE:
            mp4_path = output_dir / f"{stem}_stream.mp4"
            w, h = images[0].size
            fps = 1.0 / args.interval
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video = cv2.VideoWriter(str(mp4_path), fourcc, fps, (w, h))

            for pil_img in images:
                # Convert PIL RGB to OpenCV BGR
                cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                video.write(cv_img)
            video.release()
            print(f"🎥 MP4 Video saved: {mp4_path}")
        else:
            print("OpenCV not installed. Skipping MP4 creation.")

    if args.format in ["all", "png"]:
        print(f"PNG Frames saved to: {png_folder}")

    print(f"\nDone! Output directory: {output_dir.resolve()}")


if __name__ == "__main__":
    main()