import math
import random

import pygame

from settings import *

# --- Water colors ---
# Water gets darker the further it is from land. Land always uses LAND_COLOR,
# because nations.py paints released land back with exactly that color.
WATER_COLORS = [
    (66, 92, 100),    # shallow water right next to the coast
    (52, 76, 85),     # 2 tiles from land
    (42, 62, 71),     # 3 tiles from land
    (35, 52, 60),     # 4 tiles from land
    (29, 43, 50),     # deep water, 5 or more tiles from land
]
EDGE_DARKNESS = 0.9    # a water edge is this bright compared to its tile
DEEP_WATER_WIGGLE = 4  # deep water tiles get a tiny brightness change, so it looks less flat


def hex_center(x, y):
    center_x = x * HEX_WIDTH + HEX_WIDTH / 2
    if y % 2 == 1:
        center_x += HEX_WIDTH / 2
    center_y = y * ROW_HEIGHT + HEX_RADIUS
    return center_x, center_y


def hex_corners(x, y):
    center_x, center_y = hex_center(x, y)
    corners = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        corner_x = center_x + HEX_RADIUS * math.cos(angle)
        corner_y = center_y + HEX_RADIUS * math.sin(angle)
        corners.append((corner_x, corner_y))
    return corners


def neighbors_of(x, y):
    if y % 2 == 0:
        directions = EVEN_ROW_NEIGHBORS
    else:
        directions = ODD_ROW_NEIGHBORS
    result = []
    for dx, dy in directions:
        nx = x + dx
        ny = y + dy
        if 0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT:
            result.append((nx, ny))
    return result


def pixel_to_hex(pixel_x, pixel_y):
    guess_y = int(pixel_y // ROW_HEIGHT)
    guess_x = int(pixel_x // HEX_WIDTH)
    best = None
    best_distance = None
    for y in range(guess_y - 1, guess_y + 2):
        for x in range(guess_x - 1, guess_x + 2):
            if 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT:
                center_x, center_y = hex_center(x, y)
                distance = (pixel_x - center_x) ** 2 + (pixel_y - center_y) ** 2
                if best is None or distance < best_distance:
                    best = (x, y)
                    best_distance = distance
    return best


def make_random_map(land_chance=LAND_CHANCE, rng=random):
    # rng is where the random numbers come from. maps.py gives its own
    # random.Random(seed), so the same seed always makes the same map.
    tiles = []
    for y in range(MAP_HEIGHT):
        row = []
        for x in range(MAP_WIDTH):
            if rng.random() < land_chance:
                row.append(LAND)
            else:
                row.append(WATER)
        tiles.append(row)
    return tiles


def count_land_neighbors(tiles, x, y):
    count = 0
    for nx, ny in neighbors_of(x, y):
        if tiles[ny][nx] == LAND:
            count += 1
    return count


def smooth(tiles):
    new_tiles = []
    for y in range(MAP_HEIGHT):
        row = []
        for x in range(MAP_WIDTH):
            neighbors = count_land_neighbors(tiles, x, y)
            if neighbors >= 4:
                row.append(LAND)
            elif neighbors <= 2:
                row.append(WATER)
            else:
                row.append(tiles[y][x])
        new_tiles.append(row)
    return new_tiles


def make_map():
    # The classic map. maps.make_map has more map types.
    tiles = make_random_map()
    for _ in range(SMOOTH_STEPS):
        tiles = smooth(tiles)
    return tiles


def distance_to_land(tiles):
    # For every tile: how many steps it is to the nearest land (land itself is 0).
    # It spreads out from all the land at once, one step at a time.
    far_away = MAP_WIDTH + MAP_HEIGHT
    distances = [[far_away] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
    current = []
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            if tiles[y][x] == LAND:
                distances[y][x] = 0
                current.append((x, y))
    step = 0
    while current:
        step += 1
        next_tiles = []
        for x, y in current:
            for nx, ny in neighbors_of(x, y):
                if distances[ny][nx] > step:
                    distances[ny][nx] = step
                    next_tiles.append((nx, ny))
        current = next_tiles
    return distances


def darker(color, amount):
    return tuple(int(c * amount) for c in color)


def water_color(x, y, distance):
    # Pick a water color from how far away the land is.
    level = min(distance, len(WATER_COLORS)) - 1
    color = WATER_COLORS[level]
    if level == len(WATER_COLORS) - 1:
        # Deep water: a small brightness change that is always the same for the same tile.
        wiggle = (x * 7 + y * 13 + x * y) % (DEEP_WATER_WIGGLE * 2 + 1) - DEEP_WATER_WIGGLE
        color = tuple(max(0, min(255, c + wiggle)) for c in color)
    return color


def draw_map(tiles):
    image = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    image.fill(WATER_COLORS[-1])
    distances = distance_to_land(tiles)
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            if tiles[y][x] == LAND:
                color = LAND_COLOR
                edge_color = LAND_EDGE_COLOR
            else:
                color = water_color(x, y, distances[y][x])
                edge_color = darker(color, EDGE_DARKNESS)
            corners = hex_corners(x, y)
            pygame.draw.polygon(image, color, corners)
            pygame.draw.polygon(image, edge_color, corners, 1)
    return image


def pixel_distance(tile_a, tile_b):
    ax, ay = hex_center(tile_a[0], tile_a[1])
    bx, by = hex_center(tile_b[0], tile_b[1])
    return math.hypot(ax - bx, ay - by)
