import math
import random

import pygame

import hexmap
from settings import *

# Names of the map types you can pick. The first one is the default.
MAP_TYPES = ["Continents", "Islands", "Pangaea", "Lakes", "Two Continents", "Ring"]

SMALLEST_ISLAND = 8  # land groups smaller than this turn into water
SMALLEST_POND = 4    # water groups smaller than this turn into land


# --- Helpers ---

def make_noise(rng, cell_size):
    # "Value noise": random numbers on a coarse grid, smoothly blended between
    # the grid points. A big cell_size gives big, slow hills; a small one gives small bumps.
    # Returns a grid with a number between 0 and 1 for every tile.
    grid_width = int(MAP_WIDTH / cell_size) + 3
    grid_height = int(MAP_HEIGHT / cell_size) + 3
    grid = []
    for _ in range(grid_height):
        grid.append([rng.random() for _ in range(grid_width)])

    noise = []
    for y in range(MAP_HEIGHT):
        row = []
        for x in range(MAP_WIDTH):
            # Where this tile is on the coarse grid. Odd rows are pushed half a hexagon
            # to the right, and rows are a bit closer together than columns.
            grid_x = (x + (y % 2) * 0.5) / cell_size
            grid_y = y * (ROW_HEIGHT / HEX_WIDTH) / cell_size
            left = int(grid_x)
            top = int(grid_y)
            # How far we are between the grid points (0 to 1), made smooth with an S-curve.
            fx = grid_x - left
            fy = grid_y - top
            fx = fx * fx * (3 - 2 * fx)
            fy = fy * fy * (3 - 2 * fy)
            top_value = grid[top][left] + (grid[top][left + 1] - grid[top][left]) * fx
            bottom_value = grid[top + 1][left] + (grid[top + 1][left + 1] - grid[top + 1][left]) * fx
            row.append(top_value + (bottom_value - top_value) * fy)
        noise.append(row)
    return noise


def mixed_noise(rng, layers):
    # Adds several noise layers together. layers is a list of (cell_size, weight).
    total = [[0] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
    for cell_size, weight in layers:
        noise = make_noise(rng, cell_size)
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                total[y][x] += noise[y][x] * weight
    return total


def position(x, y):
    # Where a tile is on the map: (-1, -1) is the top left, (0, 0) the middle, (1, 1) the bottom right.
    center_x, center_y = hexmap.hex_center(x, y)
    return center_x / SCREEN_WIDTH * 2 - 1, center_y / SCREEN_HEIGHT * 2 - 1


def distance_from_center(x, y):
    # 0 in the middle of the map, 1 at the middle of an edge, more in the corners.
    px, py = position(x, y)
    return math.sqrt(px * px + py * py)


def land_from_heights(heights, land_fraction):
    # Turns a grid of "heights" into land and water: the highest tiles become land,
    # until land_fraction (for example 0.4 = 40 %) of the map is land.
    all_heights = []
    for row in heights:
        all_heights.extend(row)
    all_heights.sort()
    sea_level = all_heights[int(len(all_heights) * (1 - land_fraction))]
    tiles = []
    for row in heights:
        tiles.append([LAND if height >= sea_level else WATER for height in row])
    return tiles


def remove_small_groups(tiles, kind, min_size):
    # Finds every group of touching tiles of one kind (LAND or WATER).
    # Groups smaller than min_size are flipped to the other kind.
    other = WATER if kind == LAND else LAND
    seen = [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
    for start_y in range(MAP_HEIGHT):
        for start_x in range(MAP_WIDTH):
            if seen[start_y][start_x] or tiles[start_y][start_x] != kind:
                continue
            # Flood fill: collect the whole group this tile belongs to.
            group = []
            to_visit = [(start_x, start_y)]
            seen[start_y][start_x] = True
            while to_visit:
                x, y = to_visit.pop()
                group.append((x, y))
                for nx, ny in hexmap.neighbors_of(x, y):
                    if not seen[ny][nx] and tiles[ny][nx] == kind:
                        seen[ny][nx] = True
                        to_visit.append((nx, ny))
            if len(group) < min_size:
                for x, y in group:
                    tiles[y][x] = other


def clean_up(tiles, smallest_island=SMALLEST_ISLAND, smallest_pond=SMALLEST_POND):
    # Removes tiny islands and ponds that only look like noise.
    remove_small_groups(tiles, LAND, smallest_island)
    remove_small_groups(tiles, WATER, smallest_pond)
    return tiles


# --- The map types ---

def make_continents(rng):
    # The classic map: random land and water, smoothed into a few big continents.
    tiles = hexmap.make_random_map(LAND_CHANCE, rng)
    for _ in range(SMOOTH_STEPS):
        tiles = hexmap.smooth(tiles)
    return clean_up(tiles)


def make_islands(rng):
    # Many small islands: bumpy noise with small cells, and only a third of it becomes land.
    heights = mixed_noise(rng, [(3.5, 0.75), (1.8, 0.25)])
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            # A bit lower near the edges, so the islands don't stick to the border.
            heights[y][x] -= 0.4 * max(0, distance_from_center(x, y) - 0.85)
    tiles = land_from_heights(heights, 0.33)
    tiles = hexmap.smooth(tiles)
    return clean_up(tiles, smallest_island=6)


def make_pangaea(rng):
    # One big continent: the middle of the map is high, the edges are low,
    # and noise on top makes bays and peninsulas along the coast.
    heights = mixed_noise(rng, [(10, 0.45), (5, 0.35), (2.5, 0.2)])
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            heights[y][x] -= 0.7 * distance_from_center(x, y)
    tiles = land_from_heights(heights, 0.55)
    tiles = hexmap.smooth(tiles)
    # Remove everything except the big continent (bigger islands may stay).
    return clean_up(tiles, smallest_island=40)


def dig_river(tiles, rng):
    # A river starts at a random spot on the edge of the map and winds
    # towards a random spot near the middle. It stops when it reaches a lake.
    side = rng.choice(["top", "bottom", "left", "right"])
    if side == "top":
        x, y = rng.randrange(MAP_WIDTH), 0
    elif side == "bottom":
        x, y = rng.randrange(MAP_WIDTH), MAP_HEIGHT - 1
    elif side == "left":
        x, y = 0, rng.randrange(MAP_HEIGHT)
    else:
        x, y = MAP_WIDTH - 1, rng.randrange(MAP_HEIGHT)
    target = (rng.randrange(MAP_WIDTH // 4, MAP_WIDTH * 3 // 4),
              rng.randrange(MAP_HEIGHT // 4, MAP_HEIGHT * 3 // 4))

    for _ in range(MAP_WIDTH + MAP_HEIGHT):
        tiles[y][x] = WATER
        if (x, y) == target:
            break
        # Look at the neighbors that bring us closer to the target, and pick one at random.
        here = hexmap.pixel_distance((x, y), target)
        closer = []
        for nx, ny in hexmap.neighbors_of(x, y):
            if hexmap.pixel_distance((nx, ny), target) < here:
                closer.append((nx, ny))
        x, y = rng.choice(closer)
        if tiles[y][x] == WATER:
            break  # we reached a lake (or another river)


def make_lakes(rng):
    # Mostly land, with lakes here and there and a few rivers running into them.
    heights = mixed_noise(rng, [(9, 0.6), (4, 0.4)])
    tiles = land_from_heights(heights, 0.8)
    tiles = hexmap.smooth(tiles)
    for _ in range(rng.randint(3, 4)):
        dig_river(tiles, rng)
    return clean_up(tiles, smallest_pond=5)


def make_two_continents(rng):
    # A continent in the west and one in the east, with a narrow, winding strait between them.
    heights = mixed_noise(rng, [(10, 0.55), (5, 0.3), (2.5, 0.15)])
    wave_speed = rng.uniform(0.08, 0.16)
    wave_shift = rng.uniform(0, math.pi * 2)
    for y in range(MAP_HEIGHT):
        # The strait wiggles left and right as it goes down the map.
        strait_x = 0.08 * math.sin(y * wave_speed + wave_shift)
        for x in range(MAP_WIDTH):
            px, py = position(x, y)
            # Each continent is highest around its own middle (x = -0.5 or 0.5).
            from_middle = math.sqrt((abs(px - strait_x) - 0.5) ** 2 + py * py)
            heights[y][x] -= 0.75 * from_middle
            # Lower near the left and right edges, so there is ocean around the continents.
            heights[y][x] -= 2 * max(0, abs(px) - 0.85)
            # The strait itself is always water, about 2 tiles wide.
            if abs(px - strait_x) < 0.045:
                heights[y][x] -= 10
    tiles = land_from_heights(heights, 0.46)
    tiles = hexmap.smooth(tiles)
    return clean_up(tiles, smallest_island=20)


def make_ring(rng):
    # A ring of land around a sea in the middle of the map.
    heights = mixed_noise(rng, [(8, 0.6), (3, 0.4)])
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            # Highest at 0.66 from the middle, lower both inside and outside.
            heights[y][x] -= 2.0 * abs(distance_from_center(x, y) - 0.66)
    tiles = land_from_heights(heights, 0.42)
    tiles = hexmap.smooth(tiles)
    return clean_up(tiles, smallest_island=12)


def make_map(map_type="Continents", seed=None):
    # Returns a tiles grid (list of rows with LAND or WATER) for the chosen map type.
    # The same map type and seed always give the same map. seed None gives a random map.
    # We use our own random number maker, so the normal random module is left alone.
    rng = random.Random(seed)
    if map_type == "Islands":
        return make_islands(rng)
    elif map_type == "Pangaea":
        return make_pangaea(rng)
    elif map_type == "Lakes":
        return make_lakes(rng)
    elif map_type == "Two Continents":
        return make_two_continents(rng)
    elif map_type == "Ring":
        return make_ring(rng)
    else:
        return make_continents(rng)


def make_preview(tiles, width, height):
    # A small picture of a map, for the menus.
    return pygame.transform.smoothscale(hexmap.draw_map(tiles), (width, height))
