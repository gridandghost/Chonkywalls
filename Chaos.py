#!/usr/bin/env python3

import os
import random
from PIL import Image
from pathlib import Path
import subprocess
import time

GRID_ROWS = 6
GRID_COLS = 24
OUTER_PADDING = 30
INNER_PADDING = 12
CHUNKS = [
    (6, 3),  
    (4, 3),  
    (3, 2),  
    (2, 3),  
    (2, 2),  
    (2, 1),  
    (1, 2),  
    (1, 1),  
]


def get_screen_resolution():
    try:
        result = subprocess.run(['hyprctl', 'monitors'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if '@' in line and 'x' in line and ('HDMI' in line or 'DP' in line or 'eDP' in line):
                    parts = line.split()
                    for part in parts:
                        if 'x' in part and '@' in part:
                            resolution_part = part.split('@')[0].strip()
                            if 'x' in resolution_part:
                                width, height = map(int, resolution_part.split('x'))
                                return width, height
    except Exception:
        pass
    return 5120, 1440


def load_images(image_folder):
    supported_formats = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')
    images = []
    for file_path in Path(image_folder).glob('*'):
        if file_path.suffix.lower() in supported_formats:
            try:
                img = Image.open(file_path)
                images.append(img.convert('RGB'))
            except Exception:
                pass
    return images


def create_chunk_grid_layout(images, screen_width, screen_height):
    if not images:
        return None

    cell_width = (screen_width - 2 * OUTER_PADDING - (GRID_COLS - 1) * INNER_PADDING) // GRID_COLS
    cell_height = (screen_height - 2 * OUTER_PADDING - (GRID_ROWS - 1) * INNER_PADDING) // GRID_ROWS

    canvas = Image.new('RGB', (screen_width, screen_height), (15, 15, 20))
    grid = [[False for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    random.shuffle(images)

    def fits(chunk_w, chunk_h, row, col):
        if row + chunk_h > GRID_ROWS or col + chunk_w > GRID_COLS:
            return False
        for r in range(row, row + chunk_h):
            for c in range(col, col + chunk_w):
                if grid[r][c]:
                    return False
        return True

    def occupy(chunk_w, chunk_h, row, col):
        for r in range(row, row + chunk_h):
            for c in range(col, col + chunk_w):
                grid[r][c] = True

    image_idx = 0
    for chunk_w, chunk_h in CHUNKS * 100:  
        placed = False
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                if fits(chunk_w, chunk_h, row, col):
                    if image_idx >= len(images):
                        return canvas
                    img = images[image_idx]
                    image_idx += 1

                    x = OUTER_PADDING + col * (cell_width + INNER_PADDING)
                    y = OUTER_PADDING + row * (cell_height + INNER_PADDING)
                    w = chunk_w * cell_width + (chunk_w - 1) * INNER_PADDING
                    h = chunk_h * cell_height + (chunk_h - 1) * INNER_PADDING

                    aspect_img = img.width / img.height
                    aspect_chunk = w / h

                    if aspect_img > aspect_chunk:
                        new_height = h
                        new_width = int(h * aspect_img)
                    else:
                        new_width = w
                        new_height = int(w / aspect_img)

                    resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    offset_x = x + (w - new_width) // 2
                    offset_y = y + (h - new_height) // 2
                    canvas.paste(resized, (offset_x, offset_y))
                    occupy(chunk_w, chunk_h, row, col)
                    placed = True
                    break
            if placed:
                break
    return canvas


def main():
    image_folder = "/home/saehwa/Pictures/"
    output_filename = "/home/saehwa/Pictures/wallpaper.png"
    screen_width, screen_height = get_screen_resolution()
    images = load_images(image_folder)
    if not images:
        print("No images found.")
        return

    wallpaper = create_chunk_grid_layout(images, screen_width, screen_height)

    if wallpaper:
        try:
            wallpaper.save(output_filename, quality=95)
            print(f"\u2713 Wallpaper saved as: {output_filename}")
            subprocess.run(["swww", "img", output_filename], check=True)
            print(f"\u2713 Wallpaper applied via: swww img {output_filename}")
        except Exception as e:
            print(f"\u26a0\ufe0f Error saving or setting wallpaper: {e}")
    else:
        print("Failed to create wallpaper")


if __name__ == "__main__":
    main()
