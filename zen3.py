#!/usr/bin/env python3

import os
import random
from PIL import Image
from pathlib import Path
import subprocess
import time

GRID_ROWS = 8
GRID_COLS = 28
OUTER_PADDING = 20
INNER_PADDING = 6

CHUNKS = [
    (4, 2),  
    (3, 2), 
    (2, 3),  
    (3, 1),  
    (2, 2), 
    (1, 3),  
    (2, 1), 
    (1, 2),  
    (1, 1),  
    (4, 1),  
    (1, 4), 
    (3, 3), 
]

CHUNK_WEIGHTS = [
    2,  
    3,  
    4,   
    3,   
    5,  
    3, 
    6,   
    6,  
    10, 
    2,  
    2,   
    1,   
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

def create_freeflow_layout(images, screen_width, screen_height):
    if not images:
        return None

    print(f"Creating free-flowing layout: {GRID_COLS}x{GRID_ROWS} grid")
    
    cell_width = (screen_width - 2 * OUTER_PADDING - (GRID_COLS - 1) * INNER_PADDING) // GRID_COLS
    cell_height = (screen_height - 2 * OUTER_PADDING - (GRID_ROWS - 1) * INNER_PADDING) // GRID_ROWS

    print(f"Cell size: {cell_width}x{cell_height}")
    print(f"Padding: {OUTER_PADDING}px outer, {INNER_PADDING}px inner")

    canvas = Image.new('RGB', (screen_width, screen_height), (15, 15, 20))
    grid = [[False for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    
    shuffled_images = images.copy()
    random.shuffle(shuffled_images)

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

    def find_best_position(chunk_w, chunk_h):
        """Find the best position for a chunk, trying multiple strategies"""
        positions = []
        
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                if fits(chunk_w, chunk_h, row, col):
                    score = 0
                    neighbors = 0
                    for r in range(max(0, row-1), min(GRID_ROWS, row + chunk_h + 1)):
                        for c in range(max(0, col-1), min(GRID_COLS, col + chunk_w + 1)):
                            if grid[r][c]:
                                neighbors += 1
                    
                    score = neighbors - (row * 0.1) - (col * 0.05)  
                    positions.append((score, row, col))
        
        if positions:
            positions.sort(reverse=True)
            top_positions = positions[:min(5, len(positions))]
            return random.choice(top_positions)[1:] if top_positions else None
        return None

    def get_random_chunk():
        """Get a random chunk size based on weights"""
        return random.choices(CHUNKS, weights=CHUNK_WEIGHTS, k=1)[0]

    image_idx = 0
    placement_attempts = 0
    max_attempts = len(shuffled_images) * 3

    while image_idx < len(shuffled_images) and placement_attempts < max_attempts:
        placement_attempts += 1
        
        chunk_w, chunk_h = get_random_chunk()
        
        position = find_best_position(chunk_w, chunk_h)
        
        if position is None:
            fallback_chunks = [(2, 1), (1, 2), (1, 1)]
            for fallback_w, fallback_h in fallback_chunks:
                position = find_best_position(fallback_w, fallback_h)
                if position:
                    chunk_w, chunk_h = fallback_w, fallback_h
                    break
        
        if position is None:
            continue 
            
        row, col = position
        img = shuffled_images[image_idx]
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
            offset_x = x - (new_width - w) // 2 
            offset_y = y
        else:
            new_width = w
            new_height = int(w / aspect_img)
            offset_x = x
            offset_y = y - (new_height - h) // 2 

        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        if new_width > w or new_height > h:
            crop_x = max(0, (new_width - w) // 2)
            crop_y = max(0, (new_height - h) // 2)
            resized = resized.crop((crop_x, crop_y, crop_x + w, crop_y + h))
            offset_x = x
            offset_y = y

        canvas.paste(resized, (offset_x, offset_y))
        occupy(chunk_w, chunk_h, row, col)
        
        if image_idx % 20 == 0:
            filled_cells = sum(sum(row) for row in grid)
            total_cells = GRID_ROWS * GRID_COLS
            print(f"Placed {image_idx} images, grid {filled_cells}/{total_cells} filled ({filled_cells/total_cells*100:.1f}%)")

    filled_cells = sum(sum(row) for row in grid)
    total_cells = GRID_ROWS * GRID_COLS
    print(f"Layout complete: {image_idx} images placed, {filled_cells}/{total_cells} cells filled ({filled_cells/total_cells*100:.1f}%)")
    
    return canvas

def main():
    image_folder = "/home/saehwa/Pictures/"
    output_filename = "/home/saehwa/Pictures/wallpaper.png"
    screen_width, screen_height = get_screen_resolution()
    images = load_images(image_folder)
    if not images:
        print("No images found.")
        return

    print(f"Loaded {len(images)} images")
    wallpaper = create_freeflow_layout(images, screen_width, screen_height)

    if wallpaper:
        try:
            wallpaper.save(output_filename, quality=95)
            print(f"✓ Wallpaper saved as: {output_filename}")
            subprocess.run(["swww", "img", output_filename], check=True)
            print(f"✓ Wallpaper applied via: swww img {output_filename}")
        except Exception as e:
            print(f"⚠️ Error saving or setting wallpaper: {e}")
    else:
        print("Failed to create wallpaper")

if __name__ == "__main__":
    main()
