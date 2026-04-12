"""Genere l'icone VoixClaire (micro stylise) en .ico."""

import struct
import zlib
import os
import sys


def create_png(size):
    """Cree un PNG en memoire avec un micro stylise."""
    pixels = [[0] * size * 4 for _ in range(size)]  # RGBA

    def set_pixel(x, y, r, g, b, a=255):
        if 0 <= x < size and 0 <= y < size:
            off = x * 4
            pixels[y][off] = r
            pixels[y][off + 1] = g
            pixels[y][off + 2] = b
            pixels[y][off + 3] = a

    def fill_circle(cx, cy, radius, r, g, b, a=255):
        for y in range(max(0, int(cy - radius)), min(size, int(cy + radius + 1))):
            for x in range(max(0, int(cx - radius)), min(size, int(cx + radius + 1))):
                if (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2:
                    set_pixel(x, y, r, g, b, a)

    def fill_rounded_rect(x1, y1, x2, y2, radius, r, g, b, a=255):
        for y in range(max(0, y1), min(size, y2)):
            for x in range(max(0, x1), min(size, x2)):
                inside = False
                if x1 + radius <= x <= x2 - radius or y1 + radius <= y <= y2 - radius:
                    inside = True
                elif (x - (x1 + radius)) ** 2 + (y - (y1 + radius)) ** 2 <= radius ** 2:
                    inside = True
                elif (x - (x2 - radius)) ** 2 + (y - (y1 + radius)) ** 2 <= radius ** 2:
                    inside = True
                elif (x - (x1 + radius)) ** 2 + (y - (y2 - radius)) ** 2 <= radius ** 2:
                    inside = True
                elif (x - (x2 - radius)) ** 2 + (y - (y2 - radius)) ** 2 <= radius ** 2:
                    inside = True
                if inside:
                    set_pixel(x, y, r, g, b, a)

    def fill_rect(x1, y1, x2, y2, r, g, b, a=255):
        for y in range(max(0, y1), min(size, y2)):
            for x in range(max(0, x1), min(size, x2)):
                set_pixel(x, y, r, g, b, a)

    def draw_arc(cx, cy, radius, thickness, start_angle, end_angle, r, g, b, a=255):
        import math
        for y in range(max(0, int(cy - radius - thickness)), min(size, int(cy + radius + thickness + 1))):
            for x in range(max(0, int(cx - radius - thickness)), min(size, int(cx + radius + thickness + 1))):
                dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                if radius - thickness / 2 <= dist <= radius + thickness / 2:
                    angle = math.atan2(y - cy, x - cx)
                    if start_angle <= angle <= end_angle:
                        set_pixel(x, y, r, g, b, a)

    s = size / 256  # facteur d'echelle

    # --- Fond: cercle gradient bleu ---
    # Fond bleu fonce
    fill_circle(size // 2, size // 2, size // 2, 30, 30, 46)

    # Cercle bleu principal
    fill_circle(size // 2, size // 2, int(120 * s), 59, 130, 246)

    # Halo plus clair en haut a gauche (effet 3D)
    fill_circle(int(110 * s), int(100 * s), int(60 * s), 116, 180, 250, 100)

    # --- Tete du micro (blanc) ---
    mic_cx = size // 2
    mic_top = int(50 * s)
    mic_w = int(40 * s)
    mic_h = int(72 * s)
    mic_r = int(20 * s)

    # Corps du micro (rectangle arrondi blanc)
    fill_rounded_rect(
        mic_cx - mic_w, mic_top,
        mic_cx + mic_w, mic_top + mic_h,
        mic_r, 255, 255, 255
    )
    # Dome arrondi en haut
    fill_circle(mic_cx, mic_top + mic_r, mic_w, 255, 255, 255)
    # Bas arrondi
    fill_circle(mic_cx, mic_top + mic_h - mic_r, mic_w, 255, 255, 255)

    # Grille du micro (lignes grises)
    for i in range(4):
        line_y = mic_top + int(20 * s) + i * int(16 * s)
        fill_rect(
            mic_cx - int(28 * s), line_y,
            mic_cx + int(28 * s), line_y + int(3 * s),
            200, 200, 220
        )

    # --- Arc du support (blanc) ---
    import math
    arc_cy = mic_top + mic_h - int(5 * s)
    arc_radius = int(52 * s)
    arc_thick = int(7 * s)
    for y in range(arc_cy, min(size, arc_cy + arc_radius + arc_thick)):
        for x in range(mic_cx - arc_radius - arc_thick, mic_cx + arc_radius + arc_thick):
            if 0 <= x < size and 0 <= y < size:
                dist = ((x - mic_cx) ** 2 + (y - arc_cy) ** 2) ** 0.5
                if arc_radius - arc_thick / 2 <= dist <= arc_radius + arc_thick / 2:
                    set_pixel(x, y, 255, 255, 255)

    # --- Pied du micro ---
    foot_top = arc_cy + arc_radius - int(3 * s)
    foot_w = int(7 * s)
    fill_rect(
        mic_cx - foot_w // 2, foot_top,
        mic_cx + foot_w // 2 + 1, foot_top + int(25 * s),
        255, 255, 255
    )

    # Base du pied
    base_y = foot_top + int(22 * s)
    fill_rounded_rect(
        mic_cx - int(28 * s), base_y,
        mic_cx + int(28 * s), base_y + int(10 * s),
        int(5 * s), 255, 255, 255
    )

    # --- Petits cercles verts (ondes sonores) ---
    wave_color = (166, 227, 161)  # vert doux
    for i, radius_mult in enumerate([70, 90, 110]):
        r_wave = int(radius_mult * s)
        thick = int(4 * s)
        alpha = 200 - i * 50
        for y in range(size):
            for x in range(size):
                dist = ((x - mic_cx) ** 2 + (y - size // 2) ** 2) ** 0.5
                if r_wave - thick / 2 <= dist <= r_wave + thick / 2:
                    angle = math.atan2(y - size // 2, x - mic_cx)
                    # Seulement les cotes (pas en haut/bas)
                    if (-0.6 < angle < 0.6) or (angle > 2.5 or angle < -2.5):
                        set_pixel(x, y, *wave_color, alpha)

    # Encoder en PNG
    raw_data = b''
    for row in pixels:
        raw_data += b'\x00'  # filtre None
        raw_data += bytes(row)

    def png_chunk(chunk_type, data):
        chunk = chunk_type + data
        return struct.pack('>I', len(data)) + chunk + struct.pack('>I', zlib.crc32(chunk) & 0xFFFFFFFF)

    png = b'\x89PNG\r\n\x1a\n'
    png += png_chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
    png += png_chunk(b'IDAT', zlib.compress(raw_data, 9))
    png += png_chunk(b'IEND', b'')

    return png


def create_ico(output_path):
    """Cree un fichier .ico multi-resolution."""
    sizes = [16, 32, 48, 64, 128, 256]
    pngs = []
    for s in sizes:
        print(f"  Generation {s}x{s}...")
        pngs.append(create_png(s))

    # Format ICO
    num = len(pngs)
    header = struct.pack('<HHH', 0, 1, num)

    # Calculer les offsets
    dir_size = 6 + num * 16
    offset = dir_size
    entries = b''
    for i, (s, png) in enumerate(zip(sizes, pngs)):
        w = 0 if s == 256 else s
        h = 0 if s == 256 else s
        entries += struct.pack('<BBBBHHII', w, h, 0, 0, 1, 32, len(png), offset)
        offset += len(png)

    with open(output_path, 'wb') as f:
        f.write(header)
        f.write(entries)
        for png in pngs:
            f.write(png)

    print(f"  Icone sauvegardee: {output_path}")


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ico_path = os.path.join(script_dir, 'voixclaire.ico')
    create_ico(ico_path)
