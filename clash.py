import math
import random

import pygame

# --- Settings ---
HEX_RADIUS = 6        # distance from the middle of a hexagon to a corner
MAP_WIDTH = 90        # number of hexagons across
MAP_HEIGHT = 70       # number of hexagons down
LAND_CHANCE = 0.52    # chance that a hexagon starts as land
SMOOTH_STEPS = 5      # how many times the map gets smoothed
MIN_ROBOTS = 1        # fewest robot nations you can play against
MAX_ROBOTS = 7        # most robot nations you can play against
START_ROBOTS = 3      # where the slider starts
CAPITAL_SPACING = 120 # how far apart (in pixels) capitals try to be
CAMERA_SPEED = 10     # pixels the camera moves each frame while you hold a key
ZOOM_STEP = 1.2       # how much one click on the mouse wheel zooms
MAX_ZOOM = 5          # how far in you can zoom

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
MENU_BACKGROUND = (25, 30, 45)
MENU_TEXT_COLOR = (235, 235, 235)
HINT_COLOR = (130, 140, 160)
SLIDER_TRACK_COLOR = (80, 90, 110)
SLIDER_KNOB_COLOR = (255, 230, 80)

# --- Nation colors ---
# The first color is yours, the rest go to the robots.
NATION_COLORS = [
    (255, 255, 255),  # you
    (220, 60, 60),    # red
    (240, 150, 40),   # orange
    (160, 80, 200),   # purple
    (40, 200, 200),   # cyan
    (240, 110, 180),  # pink
    (130, 90, 50),    # brown
    (20, 20, 20),     # black
]

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


def pixel_distance(tile_a, tile_b):
    ax, ay = hex_center(tile_a[0], tile_a[1])
    bx, by = hex_center(tile_b[0], tile_b[1])
    return math.hypot(ax - bx, ay - by)


def place_capitals(tiles, count):
    land_tiles = []
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            if tiles[y][x] == LAND:
                land_tiles.append((x, y))
    random.shuffle(land_tiles)

    # First try to keep every capital far away from the others.
    capitals = []
    for tile in land_tiles:
        if len(capitals) == count:
            break
        far_enough = True
        for capital in capitals:
            if pixel_distance(tile, capital) < CAPITAL_SPACING:
                far_enough = False
        if far_enough:
            capitals.append(tile)

    # If the map was too small for that, just take any free land tile.
    for tile in land_tiles:
        if len(capitals) == count:
            break
        if tile not in capitals:
            capitals.append(tile)
    return capitals


def make_nations(tiles, robot_count):
    # One nation for you, plus one nation for every robot.
    capitals = place_capitals(tiles, robot_count + 1)
    nations = []
    for i, capital in enumerate(capitals):
        if i == 0:
            name = "You"
        else:
            name = f"Robot {i}"
        nations.append({
            "name": name,
            "color": NATION_COLORS[i],
            "capital": capital,
            "fill_color": blend(LAND_COLOR, NATION_COLORS[i], 0.6),
            "edge_color": blend(LAND_COLOR, NATION_COLORS[i], 0.75),
            "land": set(),
        })
    return nations


def draw_nations(screen, nations, font, camera):
    for nation in nations:
        x, y = nation["capital"]
        center_x, center_y = map_to_screen(hex_center(x, y), camera)
        name = font.render(nation["name"], True, MENU_TEXT_COLOR)
        shadow = font.render(nation["name"], True, (0, 0, 0))
        name_pos = name.get_rect(center=(center_x, center_y))
        screen.blit(shadow, name_pos.move(1, 1))
        screen.blit(name, name_pos)


def blend(color_a, color_b, amount):
    # Mix two colors. amount 0 gives color_a, amount 1 gives color_b.
    return tuple(int(a + (b - a) * amount) for a, b in zip(color_a, color_b))


def paint_tile(map_image, tile, nation):
    x, y = tile
    corners = hex_corners(x, y)
    pygame.draw.polygon(map_image, nation["fill_color"], corners)
    pygame.draw.polygon(map_image, nation["edge_color"], corners, 1)


def give_start_land(tiles, nations, map_image):
    # Every nation starts with its capital and the land right around it.
    # Returns a grid that says which nation owns each tile (None means nobody).
    owners = [[None] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
    for i, nation in enumerate(nations):
        x, y = nation["capital"]
        start_tiles = [(x, y)] + neighbors_of(x, y)
        for tx, ty in start_tiles:
            if tiles[ty][tx] == LAND and owners[ty][tx] is None:
                owners[ty][tx] = i
                nation["land"].add((tx, ty))
                paint_tile(map_image, (tx, ty), nation)
    return owners


def screen_to_map(pos, camera):
    # Turns a point on the screen into a point on the map.
    return pos[0] / camera["zoom"] + camera["x"], pos[1] / camera["zoom"] + camera["y"]


def map_to_screen(pos, camera):
    # Turns a point on the map into a point on the screen.
    return (pos[0] - camera["x"]) * camera["zoom"], (pos[1] - camera["y"]) * camera["zoom"]


def clamp_camera(camera):
    # Stop the camera from showing anything outside the map.
    view_width = SCREEN_WIDTH / camera["zoom"]
    view_height = SCREEN_HEIGHT / camera["zoom"]
    camera["x"] = max(0, min(SCREEN_WIDTH - view_width, camera["x"]))
    camera["y"] = max(0, min(SCREEN_HEIGHT - view_height, camera["y"]))


def move_camera(camera):
    keys = pygame.key.get_pressed()
    step = CAMERA_SPEED / camera["zoom"]
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        camera["x"] -= step
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        camera["x"] += step
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        camera["y"] -= step
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        camera["y"] += step
    clamp_camera(camera)


def zoom_camera(camera, mouse_pos, steps):
    # Zoom in (steps > 0) or out (steps < 0) while keeping the spot under the mouse still.
    map_x, map_y = screen_to_map(mouse_pos, camera)
    camera["zoom"] = max(1, min(MAX_ZOOM, camera["zoom"] * ZOOM_STEP ** steps))
    camera["x"] = map_x - mouse_pos[0] / camera["zoom"]
    camera["y"] = map_y - mouse_pos[1] / camera["zoom"]
    clamp_camera(camera)


def draw_view(screen, map_image, camera):
    # Cut out the part of the map the camera sees and stretch it over the whole screen.
    view = pygame.Rect(int(camera["x"]), int(camera["y"]),
                       int(SCREEN_WIDTH / camera["zoom"]), int(SCREEN_HEIGHT / camera["zoom"]))
    part = map_image.subsurface(view)
    screen.blit(pygame.transform.scale(part, (SCREEN_WIDTH, SCREEN_HEIGHT)), (0, 0))


def slider_value_from_mouse(mouse_x, track):
    # Turns the mouse's x position into a number between MIN_ROBOTS and MAX_ROBOTS.
    fraction = (mouse_x - track.left) / track.width
    fraction = max(0, min(1, fraction))
    return MIN_ROBOTS + round(fraction * (MAX_ROBOTS - MIN_ROBOTS))


def start_screen(screen, clock):
    # Returns how many robots to play against, or None if the window was closed.
    title_font = pygame.font.SysFont(None, 96)
    font = pygame.font.SysFont(None, 32)
    center_x = SCREEN_WIDTH // 2
    track = pygame.Rect(center_x - 200, SCREEN_HEIGHT // 2, 400, 8)
    robots = START_ROBOTS
    dragging = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                elif event.key == pygame.K_RETURN:
                    return robots
                elif event.key == pygame.K_LEFT:
                    robots = max(MIN_ROBOTS, robots - 1)
                elif event.key == pygame.K_RIGHT:
                    robots = min(MAX_ROBOTS, robots + 1)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if track.inflate(30, 40).collidepoint(event.pos):
                    dragging = True
                    robots = slider_value_from_mouse(event.pos[0], track)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging = False
            elif event.type == pygame.MOUSEMOTION and dragging:
                robots = slider_value_from_mouse(event.pos[0], track)

        screen.fill(MENU_BACKGROUND)
        title = title_font.render("CLASH", True, MENU_TEXT_COLOR)
        screen.blit(title, title.get_rect(center=(center_x, SCREEN_HEIGHT // 3)))

        label = font.render(f"Robot nations: {robots}", True, MENU_TEXT_COLOR)
        screen.blit(label, label.get_rect(center=(center_x, track.top - 40)))
        pygame.draw.rect(screen, SLIDER_TRACK_COLOR, track, border_radius=4)
        knob_x = track.left + (robots - MIN_ROBOTS) / (MAX_ROBOTS - MIN_ROBOTS) * track.width
        pygame.draw.circle(screen, SLIDER_KNOB_COLOR, (knob_x, track.centery), 14)

        hint = font.render("Drag the slider, then press Enter", True, HINT_COLOR)
        screen.blit(hint, hint.get_rect(center=(center_x, track.bottom + 80)))

        pygame.display.flip()
        clock.tick(60)


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Clash")
    clock = pygame.time.Clock()
    name_font = pygame.font.SysFont(None, 22)

    robot_count = start_screen(screen, clock)
    if robot_count is None:
        pygame.quit()
        return

    tiles = make_map()
    map_image = draw_map(tiles)
    nations = make_nations(tiles, robot_count)
    owners = give_start_land(tiles, nations, map_image)
    selected = None
    camera = {"x": 0, "y": 0, "zoom": 1}

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    tiles = make_map()
                    map_image = draw_map(tiles)
                    nations = make_nations(tiles, robot_count)
                    owners = give_start_land(tiles, nations, map_image)
                    selected = None
                elif event.key == pygame.K_ESCAPE:
                    running = False
            elif event.type == pygame.MOUSEWHEEL:
                zoom_camera(camera, pygame.mouse.get_pos(), event.y)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                map_x, map_y = screen_to_map(event.pos, camera)
                selected = pixel_to_hex(map_x, map_y)
                x, y = selected
                if tiles[y][x] == LAND:
                    print(f"Tile ({x}, {y}): land")
                else:
                    print(f"Tile ({x}, {y}): water")

        move_camera(camera)
        draw_view(screen, map_image, camera)
        draw_nations(screen, nations, name_font, camera)
        if selected is not None:
            x, y = selected
            corners = [map_to_screen(corner, camera) for corner in hex_corners(x, y)]
            pygame.draw.polygon(screen, SELECTED_COLOR, corners, 2)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
