import random

import pygame

from settings import *
from hexmap import hex_corners, neighbors_of, pixel_distance

# --- Robot names ---
# Every game the robots get a few of these names, picked at random.
ROBOT_NAMES = [
    "Northreach", "Ashvale", "Stormhold", "Ironmere", "Duskwood", "Highcrest",
    "Frostmark", "Emberfall", "Goldmoor", "Ravenspire", "Saltcliff", "Thornwall",
    "Brightwater", "Oakheart", "Mistvale", "Redfield", "Stonebrook", "Wolfden",
    "Sunhaven", "Blackmarsh", "Silverpeak", "Greywatch", "Coldharbor", "Amberlake",
]


def blend(color_a, color_b, amount):
    # Mix two colors. amount 0 gives color_a, amount 1 gives color_b.
    return tuple(int(a + (b - a) * amount) for a, b in zip(color_a, color_b))


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
    robot_names = random.sample(ROBOT_NAMES, len(capitals) - 1)
    nations = []
    for i, capital in enumerate(capitals):
        if i == 0:
            name = "You"
            capital = None  # you pick your own start spot
        else:
            name = robot_names[i - 1]
        nations.append({
            "name": name,
            "color": NATION_COLORS[i],
            "capital": capital,
            "fill_color": blend(LAND_COLOR, NATION_COLORS[i], 0.6),
            "edge_color": blend(LAND_COLOR, NATION_COLORS[i], 0.75),
            "land": set(),
            "troops": START_TROOPS,
            "is_robot": i > 0,
            "strength": ROBOT_STRENGTH if i > 0 else 1,  # robots.py changes this with the difficulty
        })
    return nations


def max_troops(nation):
    # More land gives more troops, but every new tile gives a little less than the last.
    most = TROOP_BASE + TROOPS_PER_LAND * len(nation["land"]) ** 0.6
    if nation["is_robot"]:
        most *= nation.get("strength", ROBOT_STRENGTH)
    return most


def grow_troops(nations, seconds):
    for nation in nations:
        if not nation["land"]:
            nation["troops"] = 0  # a nation with no land is out of the game
            continue
        most = max_troops(nation)
        # Many troops grow fast, but growth slows down close to the max.
        # It never gets slower than MIN_GROWTH_PART, so the troops really reach the max
        # instead of creeping towards it one troop at a time.
        growth = TROOP_GROWTH + nation["troops"] ** 0.73 / 4
        growth *= max(MIN_GROWTH_PART, 1 - nation["troops"] / most)
        nation["troops"] = min(most, nation["troops"] + growth * seconds)


def format_troops(troops):
    # Short, calm numbers for the screen: 950, 1.2k, 12k.
    # Exact numbers change every frame and flicker, these only change now and then.
    troops = int(troops)
    if troops < 1000:
        return str(troops)
    if troops < 10000:
        return f"{troops / 1000:.1f}k"
    return f"{troops // 1000}k"


def paint_tile(map_image, tile, nation):
    x, y = tile
    corners = hex_corners(x, y)
    pygame.draw.polygon(map_image, nation["fill_color"], corners)
    pygame.draw.polygon(map_image, nation["edge_color"], corners, 1)


def claim_start_land(tiles, owners, nations, i, map_image):
    # Nation number i gets its capital and the free land right around it.
    nation = nations[i]
    x, y = nation["capital"]
    start_tiles = [(x, y)] + neighbors_of(x, y)
    for tx, ty in start_tiles:
        if tiles[ty][tx] == LAND and owners[ty][tx] is None:
            owners[ty][tx] = i
            nation["land"].add((tx, ty))
            paint_tile(map_image, (tx, ty), nation)


def give_start_land(tiles, nations, map_image):
    # Every robot starts with its capital and the land right around it.
    # You don't have a capital yet, because you pick your own spot.
    # Returns a grid that says which nation owns each tile (None means nobody).
    owners = [[None] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
    for i, nation in enumerate(nations):
        if nation["capital"] is not None:
            claim_start_land(tiles, owners, nations, i, map_image)
    return owners


def choose_start(tiles, owners, nations, tile, map_image):
    # Moves your start to the tile you clicked. Returns False if you can't start there.
    x, y = tile
    if tiles[y][x] != LAND or owners[y][x] not in (None, 0):
        return False
    you = nations[0]
    # Give back the land from your last pick, so it turns green again.
    for old_x, old_y in you["land"]:
        owners[old_y][old_x] = None
        corners = hex_corners(old_x, old_y)
        pygame.draw.polygon(map_image, LAND_COLOR, corners)
        pygame.draw.polygon(map_image, LAND_EDGE_COLOR, corners, 1)
    you["land"] = set()
    you["capital"] = tile
    claim_start_land(tiles, owners, nations, 0, map_image)
    return True
