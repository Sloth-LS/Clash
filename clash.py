import math
import random

import pygame

# --- Settings ---
HEX_RADIUS = 6        # distance from the middle of a hexagon to a corner
MAP_WIDTH = 90        # number of hexagons across
MAP_HEIGHT = 70       # number of hexagons down
LAND_CHANCE = 0.52    # chance that a hexagon starts as land
SMOOTH_STEPS = 5      # how many times the map gets smoothed

# --- Hexagon measurements ---
HEX_WIDTH = math.sqrt(3) * HEX_RADIUS   # width of one hexagon
ROW_HEIGHT = 1.5 * HEX_RADIUS           # how far down each new row starts
SCREEN_WIDTH = int(MAP_WIDTH * HEX_WIDTH + HEX_WIDTH / 2) + 1
SCREEN_HEIGHT = int(MAP_HEIGHT * ROW_HEIGHT + HEX_RADIUS / 2) + 1

# --- Tile types ---
WATER = 0
LAND = 1

# --- Colors (red, green, blue) ---
WATER_COLOR = (40, 90, 160)
LAND_COLOR = (90, 160, 70)
WATER_EDGE_COLOR = (35, 80, 145)
LAND_EDGE_COLOR = (75, 140, 60)
SELECTED_COLOR = (255, 230, 80)

# --- Neighbor directions ---
# Odd rows are pushed half a hexagon to the right,
# so even and odd rows have different neighbors.
EVEN_ROW_NEIGHBORS = [(-1, 0), (1, 0), (-1, -1), (0, -1), (-1, 1), (0, 1)]
ODD_ROW_NEIGHBORS = [(-1, 0), (1, 0), (0, -1), (1, -1), (0, 1), (1, 1)]


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


def make_random_map():
    tiles = []
    for y in range(MAP_HEIGHT):
        row = []
        for x in range(MAP_WIDTH):
            if random.random() < LAND_CHANCE:
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
    tiles = make_random_map()
    for _ in range(SMOOTH_STEPS):
        tiles = smooth(tiles)
    return tiles


def draw_map(tiles):
    image = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    image.fill(WATER_COLOR)
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            if tiles[y][x] == LAND:
                color = LAND_COLOR
                edge_color = LAND_EDGE_COLOR
            else:
                color = WATER_COLOR
                edge_color = WATER_EDGE_COLOR
            corners = hex_corners(x, y)
            pygame.draw.polygon(image, color, corners)
            pygame.draw.polygon(image, edge_color, corners, 1)
    return image


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Clash")
    clock = pygame.time.Clock()

    tiles = make_map()
    map_image = draw_map(tiles)
    selected = None

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    tiles = make_map()
                    map_image = draw_map(tiles)
                    selected = None
                elif event.key == pygame.K_ESCAPE:
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_x, mouse_y = event.pos
                selected = pixel_to_hex(mouse_x, mouse_y)
                x, y = selected
                if tiles[y][x] == LAND:
                    print(f"Tile ({x}, {y}): land")
                else:
                    print(f"Tile ({x}, {y}): water")

        screen.blit(map_image, (0, 0))
        if selected is not None:
            x, y = selected
            pygame.draw.polygon(screen, SELECTED_COLOR, hex_corners(x, y), 2)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()