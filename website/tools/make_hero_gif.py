#!/usr/bin/env python3
"""Create the 4-second looping hero from the first 5 seconds of source video.

Requires macOS Swift/AVFoundation and Pillow; these are authoring dependencies
only. Usage: python3 website/tools/make_hero_gif.py source.mp4
"""
import subprocess
import sys
import tempfile
from pathlib import Path
from PIL import Image

TOOLS = Path(__file__).resolve().parent
ASSETS = TOOLS.parent / 'assets'
with tempfile.TemporaryDirectory(prefix='enhancers-gif-') as temp:
    frames_dir = Path(temp) / 'frames'
    subprocess.run(['swift', '-suppress-warnings', '-module-cache-path', str(Path(temp) / 'swift-cache'),
                    str(TOOLS / 'extract_hero_frames.swift'), sys.argv[1], str(frames_dir)], check=True)
    frames = [Image.open(p).convert('RGB') for p in sorted(frames_dir.glob('*.png'))]
    assert len(frames) == 80 and frames[0].size == (640, 360)
    # Use one palette for the whole loop to prevent color flicker. Quantize
    # directly from lossless frames so video noise does not become GIF dithering.
    samples = Image.new('RGB', (160 * 8, 90))
    for i, frame in enumerate(frames[::10]):
        samples.paste(frame.resize((160, 90)), (160 * i, 0))
    palette = samples.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    output = ASSETS / 'dna-helix-loop.gif'
    indexed[0].save(output, save_all=True, append_images=indexed[1:], loop=0,
                    duration=50, optimize=True, disposal=1)
    frames[0].save(ASSETS / 'dna-helix-loop-poster.jpg', quality=90)
    print(f'{output.name}: {output.stat().st_size:,} bytes; 80 frames; 20 fps; infinite repeat')
