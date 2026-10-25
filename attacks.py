import pygame

from settings import *
from hexmap import hex_center, hex_corners, neighbors_of
from nations import paint_tile
from camera import map_to_screen

# --- Maneuver settings ---
DOUBLE_CLICK_TIME = 300       # milliseconds: a 2nd click this fast makes a spearhead
DOUBLE_CLICK_DISTANCE = 3     # tiles: how close the 2nd click must be to the 1st one

SPEARHEAD_WIDTH = 2           # front tiles a spearhead takes each step
SPEARHEAD_DISCOUNT = 0.7      # a spearhead pays 30 % less per tile
SUPPLY_RANGE = 6              # tiles a spearhead can go from its start without losses
SUPPLY_LOSS = 0.03            # part of its troops lost per second for every tile beyond that
SUPPLY_LOSS_MAX = 0.5         # it never loses more than this part per second

# On a hex grid a tile on a straight border already touches 2 of your tiles,
# so a real flank (attacked from more sides) starts at 3 tiles.
FLANK_TOUCHES = 3             # tiles touching an enemy tile for a flank
FLANK_DISCOUNT = 0.8          # 20 % cheaper
BIG_FLANK_TOUCHES = 4         # tiles touching an enemy tile for a big flank
BIG_FLANK_DISCOUNT = 0.6      # 40 % cheaper

POCKET_CHECK_TIME = 0.5       # seconds between each search for cut-off pockets
POCKET_TILE_COST = 1          # troops it costs to take one tile in a pocket
POCKET_DRAIN = 0.05           # part of its troops a nation with pockets loses each second
POCKET_FULL_DRAIN = 20        # pocket tiles needed for the full drain (fewer drain less)

SCORCH_RADIUS = 2             # tiles around the click that are given up
SCORCH_COST = 2               # troops it costs to give up one tile
SCORCH_TIME = 30              # seconds enemies pay more for scorched tiles
SCORCH_PRICE = 2              # enemies pay this many times the cost for a scorched tile

DIG_RADIUS = 3                # border tiles this close to the click are dug in
DIG_UPKEEP = 0.2              # troops each dug-in tile costs every second
DIG_PRICE = 1.5               # enemies pay 50 % more for a dug-in tile

FEINT_TIME = 5                # seconds before a feint goes home
FEINT_TILES_PER_SECOND = 2    # a feint only creeps forward this fast

ARROW_COUNT = 4               # small arrows drawn on each front

# --- Maneuver colors ---
DUG_IN_COLOR = (30, 30, 30)
SCORCHED_COLOR = (90, 50, 20, 120)   # the last number is how see-through it is
SPEARHEAD_COLOR = (242, 164, 46)     # amber, like the rest of the War Command look
PLAYER_ARROW_COLOR = (242, 164, 46)  # your arrows are amber, so you see them right away
ARROW_SHADOW_COLOR = (0, 0, 0)

overlay = None  # a see-through layer for tints, made the first time it is needed


# --- Small hex helpers ---

def hex_distance(tile_a, tile_b):
    # Number of steps between two tiles. Odd rows are shifted, so we first turn
    # the tiles into "cube" numbers, where the distance is easy to count.
    ax, ay = tile_a
    bx, by = tile_b
    aq = ax - (ay - (ay % 2)) // 2
    bq = bx - (by - (by % 2)) // 2
    dq = aq - bq
    dr = ay - by
    return (abs(dq) + abs(dr) + abs(dq + dr)) // 2


def tiles_near(tile, radius):
    # All map tiles within radius steps of tile.
    x, y = tile
    result = []
    for ny in range(y - radius, y + radius + 1):
        for nx in range(x - radius - 1, x + radius + 2):
            if 0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT:
                if hex_distance(tile, (nx, ny)) <= radius:
                    result.append((nx, ny))
    return result


def nearest_own_tile(game, nation_number, goal):
    # The tile of the nation that is closest to goal (None if it has no land).
    land = game["nations"][nation_number]["land"]
    if not land:
        return None
    return min(land, key=lambda tile: hex_distance(tile, goal))


def owner_of(game, tile):
    x, y = tile
    return game["owners"][y][x]


# --- Starting and stopping attacks ---

def find_front(game, attacker, target):
    # Finds the target's tiles that touch the attacker's land (target None means free land).
    # For every tile it counts how many of the attacker's tiles it touches.
    tiles = game["tiles"]
    owners = game["owners"]
    front = {}
    for x, y in game["nations"][attacker]["land"]:
        for nx, ny in neighbors_of(x, y):
            if tiles[ny][nx] == LAND and owners[ny][nx] == target:
                front[(nx, ny)] = front.get((nx, ny), 0) + 1
    return front


def start_attack(game, attacker, target, percent, kind="broad"):
    # Sends a part of the attacker's troops (percent 0.2 = 20 %) against target.
    # target is a nation number, or None for free land.
    # kind is "broad" (the normal front), "spearhead" or "feint". Returns the attack.
    nation = game["nations"][attacker]
    troops = max(0, nation["troops"]) * percent
    nation["troops"] -= troops
    # If we already attack the same target, just send more troops to that attack.
    # A feint only joins a feint, and a real attack only joins a real attack.
    for attack in game["attacks"]:
        if attack["attacker"] == attacker and attack["target"] == target:
            if (attack.get("kind") == "feint") == (kind == "feint"):
                attack["troops"] += troops
                return attack
    attack = {"attacker": attacker, "target": target, "troops": troops, "kind": kind}
    game["attacks"].append(attack)
    return attack


def end_attack(game, attack):
    # The troops that are left come home.
    game["nations"][attack["attacker"]]["troops"] += max(0, attack["troops"])
    attack["troops"] = 0
    if attack in game["attacks"]:
        game["attacks"].remove(attack)


def cancel_attacks(game, attacker, target):
    # Stops every attack of attacker against target. Returns True if there was one.
    found = False
    for attack in list(game["attacks"]):
        if attack["attacker"] == attacker and attack["target"] == target:
            end_attack(game, attack)
            found = True
    return found


def make_spearhead(game, attack, goal):
    # Turns an attack into a spearhead that pushes toward goal.
    start = nearest_own_tile(game, attack["attacker"], goal)
    if start is None:
        return
    attack["kind"] = "spearhead"
    attack["goal"] = goal
    attack["start"] = start
    attack["tip"] = start  # the tile the spearhead took last


def start_feint(game, attacker, target, percent, goal):
    # A feint looks like a big attack, creeps forward and goes home after FEINT_TIME.
    attack = start_attack(game, attacker, target, percent, "feint")
    attack["age"] = 0
    attack["progress"] = 0
    attack["goal"] = goal
    attack["start"] = nearest_own_tile(game, attacker, goal)
    return attack


# --- Prices ---

def attack_cost(game, attack, tile=None, touches=1):
    # Returns how many troops the attacker and the defender lose for one tile.
    # Without a tile you get the normal price of the attack.
    if attack["target"] is None:
        cost, defender_loss = FREE_TILE_COST, 0
    else:
        defender = game["nations"][attack["target"]]
        density = defender["troops"] / max(1, len(defender["land"]))  # troops on each tile
        ratio = defender["troops"] / max(1, attack["troops"])
        ratio = min(max(ratio, 0.6), 2)  # a big army helps, but only up to a point
        cost, defender_loss = ratio * (ENEMY_TILE_COST + density), density
    if tile is None:
        return cost, defender_loss
    return tile_cost(game, attack, tile, touches, cost, defender_loss)


def tile_cost(game, attack, tile, touches, cost, defender_loss):
    # Changes the normal price with the maneuvers that touch this tile.
    target = attack["target"]
    if target is not None and tile in game.get("pockets", {}).get(target, ()):
        return POCKET_TILE_COST, 0  # cut-off defenders are easy to beat
    if target is not None:
        if touches >= BIG_FLANK_TOUCHES:
            cost *= BIG_FLANK_DISCOUNT
        elif touches >= FLANK_TOUCHES:
            cost *= FLANK_DISCOUNT
    if game.get("dug_in", {}).get(tile) == target and target is not None:
        cost *= DIG_PRICE
    scorched = game.get("scorched", {}).get(tile)
    if scorched is not None and scorched["nation"] != attack["attacker"]:
        cost *= SCORCH_PRICE
    if attack.get("kind") == "spearhead":
        cost *= SPEARHEAD_DISCOUNT
    return cost, defender_loss


# --- Taking tiles ---

def take_tile(game, tile, attacker):
    # The attacker gets the tile, and the old owner (if any) loses it.
    x, y = tile
    nations = game["nations"]
    old_owner = game["owners"][y][x]
    if old_owner is not None:
        nations[old_owner]["land"].discard(tile)
    game["owners"][y][x] = attacker
    nations[attacker]["land"].add(tile)
    paint_tile(game["map_image"], tile, nations[attacker])


def release_tile(game, tile):
    # The tile becomes free land again.
    x, y = tile
    old_owner = game["owners"][y][x]
    if old_owner is not None:
        game["nations"][old_owner]["land"].discard(tile)
    game["owners"][y][x] = None
    corners = hex_corners(x, y)
    pygame.draw.polygon(game["map_image"], LAND_COLOR, corners)
    pygame.draw.polygon(game["map_image"], LAND_EDGE_COLOR, corners, 1)


def a_neighbor_of(game, tile, nation_number):
    # One of the nation's tiles next to tile (used to draw arrows).
    for neighbor in neighbors_of(*tile):
        if owner_of(game, neighbor) == nation_number:
            return neighbor
    return tile


def choose_tiles(game, attack, front):
    # Picks which front tiles the attack tries to take this step.
    kind = attack.get("kind", "broad")
    if kind == "spearhead":
        goal = attack["goal"]
        order = sorted(front, key=lambda tile: (hex_distance(tile, goal), -front[tile]))
        return order[:SPEARHEAD_WIDTH]
    # Tiles that touch most of our land go first, so the border grows smoothly.
    order = sorted(front, key=front.get, reverse=True)
    if kind == "feint":
        attack["progress"] += FEINT_TILES_PER_SECOND * ATTACK_STEP
        count = int(attack["progress"])
        attack["progress"] -= count
        return order[:count]
    if attack["target"] is None:
        speed = FREE_LAND_SPEED
    else:
        speed = ENEMY_LAND_SPEED
    count = max(1, int(len(front) * speed))
    return order[:count]


def move_attack(game, attack):
    # Moves one attack one step forward. Returns False when the attack is over.
    attacker = attack["attacker"]
    front = find_front(game, attacker, attack["target"])
    if not front:
        return False
    taken = []
    could_not_pay = False
    for tile in choose_tiles(game, attack, front):
        cost, defender_loss = attack_cost(game, attack, tile, front[tile])
        if attack["troops"] < cost:
            could_not_pay = True
            continue
        attack["troops"] -= cost
        if attack["target"] is not None:
            defender = game["nations"][attack["target"]]
            defender["troops"] = max(0, defender["troops"] - defender_loss)
        take_tile(game, tile, attacker)
        taken.append(tile)

    if taken:
        remember_arrows(game, attack, taken)
    if attack.get("kind") == "spearhead":
        if taken:
            goal = attack["goal"]
            attack["tip"] = min(taken, key=lambda tile: hex_distance(tile, goal))
        pay_supply(attack)
        if owner_of(game, attack["goal"]) != attack["target"]:
            return False  # we reached the goal (or someone else took it)
    if attack.get("kind") == "feint":
        attack["age"] += ATTACK_STEP
        if attack["age"] >= FEINT_TIME:
            return False
    if could_not_pay and not taken:
        return False  # too few troops to pay for any tile
    cost, _ = attack_cost(game, attack)
    if attack["troops"] < cost * 0.5:
        return False  # not even enough for the cheapest tiles
    return True


def remember_arrows(game, attack, taken):
    # Keeps a few (from, to) pairs, so draw_attacks can show arrows on the front.
    step = max(1, len(taken) // ARROW_COUNT)
    arrows = []
    for tile in taken[::step][:ARROW_COUNT]:
        arrows.append((a_neighbor_of(game, tile, attack["attacker"]), tile))
    attack["arrows"] = arrows


def pay_supply(attack):
    # A spearhead far from where it started loses troops on the long supply line.
    reach = hex_distance(attack["start"], attack["tip"])
    beyond = reach - SUPPLY_RANGE
    if beyond > 0:
        loss = min(SUPPLY_LOSS_MAX, SUPPLY_LOSS * beyond) * ATTACK_STEP
        attack["troops"] *= 1 - loss


# --- Pockets (encirclement) ---

def find_pockets(game, nation_number):
    # Tiles of the nation that have no path through its own land to its capital.
    nation = game["nations"][nation_number]
    capital = nation["capital"]
    if capital is None or capital not in nation["land"]:
        return set()  # without its capital tile nothing counts as cut off
    land = nation["land"]
    reached = {capital}
    todo = [capital]
    while todo:
        tile = todo.pop()
        for neighbor in neighbors_of(*tile):
            if neighbor in land and neighbor not in reached:
                reached.add(neighbor)
                todo.append(neighbor)
    return land - reached


def update_pockets(game):
    # Looks for pockets now and then, and drains nations that have them.
    game["pocket_timer"] = game.get("pocket_timer", 0) + ATTACK_STEP
    if "pockets" not in game or game["pocket_timer"] >= POCKET_CHECK_TIME:
        game["pocket_timer"] = 0
        game["pockets"] = {}
        for number in range(len(game["nations"])):
            pockets = find_pockets(game, number)
            if pockets:
                game["pockets"][number] = pockets
    for number, pockets in game["pockets"].items():
        nation = game["nations"][number]
        size = min(1, len(pockets) / POCKET_FULL_DRAIN)
        nation["troops"] *= 1 - POCKET_DRAIN * size * ATTACK_STEP


# --- Dig in and scorched earth ---

def border_tiles(game, nation_number, tile, radius):
    # The nation's tiles near tile that touch another nation's land.
    result = []
    for near in tiles_near(tile, radius):
        if owner_of(game, near) != nation_number:
            continue
        for neighbor in neighbors_of(*near):
            other = owner_of(game, neighbor)
            if other is not None and other != nation_number:
                result.append(near)
                break
    return result


def toggle_dig_in(game, nation_number, tile):
    # Digs in the border around tile, or stops digging in if it already is.
    dug_in = game.setdefault("dug_in", {})
    if dug_in.get(tile) == nation_number:
        for near in tiles_near(tile, DIG_RADIUS):
            if dug_in.get(near) == nation_number:
                del dug_in[near]
        return True
    border = border_tiles(game, nation_number, tile, DIG_RADIUS)
    for near in border:
        dug_in[near] = nation_number
    return len(border) > 0


def update_dig_in(game):
    # Dug-in tiles cost troops every second. Lost tiles stop being dug in.
    dug_in = game.get("dug_in")
    if not dug_in:
        return
    counts = {}
    for tile, number in list(dug_in.items()):
        if owner_of(game, tile) != number:
            del dug_in[tile]
        else:
            counts[number] = counts.get(number, 0) + 1
    for number, count in counts.items():
        nation = game["nations"][number]
        upkeep = count * DIG_UPKEEP * ATTACK_STEP
        if nation["troops"] >= upkeep:
            nation["troops"] -= upkeep
        else:
            # Too few troops to stay dug in: everyone climbs out.
            for tile in [t for t, n in dug_in.items() if n == number]:
                del dug_in[tile]


def scorch_earth(game, nation_number, tile):
    # Gives up the nation's land around tile. Returns how many tiles were given up.
    nation = game["nations"][nation_number]
    scorched = game.setdefault("scorched", {})
    count = 0
    for near in tiles_near(tile, SCORCH_RADIUS):
        if owner_of(game, near) != nation_number or near == nation["capital"]:
            continue  # the capital is never given up
        if nation["troops"] < SCORCH_COST:
            break
        nation["troops"] -= SCORCH_COST
        release_tile(game, near)
        scorched[near] = {"nation": nation_number, "until": game["time"] + SCORCH_TIME}
        count += 1
    return count


def update_scorched(game):
    # Scorched tiles stop being special after SCORCH_TIME or when someone takes them.
    scorched = game.get("scorched")
    if not scorched:
        return
    for tile, mark in list(scorched.items()):
        if mark["until"] <= game["time"] or owner_of(game, tile) is not None:
            del scorched[tile]


# --- Every step ---

def update_attacks(game):
    # Moves every attack one step forward. Called every ATTACK_STEP seconds.
    update_pockets(game)
    update_dig_in(game)
    update_scorched(game)
    for attack in list(game["attacks"]):  # a copy, because we remove finished attacks
        if not move_attack(game, attack):
            end_attack(game, attack)


# --- Mouse ---

def is_double_click(game, tile, target):
    # True if the last click was on the same target, close by and just now.
    last = game.get("last_click")
    if last is None:
        return False
    fast = pygame.time.get_ticks() - last["ticks"] <= DOUBLE_CLICK_TIME
    close = hex_distance(last["tile"], tile) <= DOUBLE_CLICK_DISTANCE
    return fast and close and last["target"] == target and last["attack"] in game["attacks"]


def handle_left_click(game, tile, target):
    mods = pygame.key.get_mods()
    if target == 0:
        if pygame.key.get_pressed()[pygame.K_r]:
            if scorch_earth(game, 0, tile) > 0:
                return "click"
        return None
    percent = game["attack_percent"]
    if mods & pygame.KMOD_SHIFT:
        percent = min(1, percent * 2)  # Shift+click sends twice as many
    if mods & pygame.KMOD_CTRL:
        start_feint(game, 0, target, percent, tile)
        return "attack"
    if is_double_click(game, tile, target):
        make_spearhead(game, game["last_click"]["attack"], tile)
        game["last_click"] = None  # a 3rd click is a normal click again
        return "attack"
    attack = start_attack(game, 0, target, percent)
    game["last_click"] = {"ticks": pygame.time.get_ticks(), "tile": tile,
                          "target": target, "attack": attack}
    return "attack"


def handle_right_click(game, tile, target):
    if target == 0:
        if toggle_dig_in(game, 0, tile):
            return "click"
        return None
    if cancel_attacks(game, 0, target):
        return "click"
    return None


def handle_click(game, tile, event):
    # A mouse click on the map after the game has started.
    # Returns the name of the sound to play, or None.
    x, y = tile
    if game["tiles"][y][x] != LAND:
        return None
    target = game["owners"][y][x]
    if event.button == 1:
        return handle_left_click(game, tile, target)
    if event.button == 3:
        return handle_right_click(game, tile, target)
    return None


# --- Drawing ---

def tile_on_screen(tile, camera):
    return map_to_screen(hex_center(*tile), camera)


def draw_arrow(surface, start, end, color, width, head):
    # A line from start to end with a triangle at the end.
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = max(0.001, (dx * dx + dy * dy) ** 0.5)
    ux, uy = dx / length, dy / length  # one pixel along the arrow
    back = (end[0] - ux * head, end[1] - uy * head)
    left = (back[0] - uy * head * 0.6, back[1] + ux * head * 0.6)
    right = (back[0] + uy * head * 0.6, back[1] - ux * head * 0.6)
    pygame.draw.line(surface, color, start, back, width)
    pygame.draw.polygon(surface, color, [end, left, right])


def draw_dashed_line(surface, start, end, color, width, dash):
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = (dx * dx + dy * dy) ** 0.5
    pieces = int(length // dash)
    for i in range(0, pieces, 2):
        a = (start[0] + dx * i / pieces, start[1] + dy * i / pieces)
        b = (start[0] + dx * (i + 1) / pieces, start[1] + dy * (i + 1) / pieces)
        pygame.draw.line(surface, color, a, b, width)


def get_overlay(screen):
    # A see-through surface as big as the screen, made only once.
    global overlay
    if overlay is None or overlay.get_size() != screen.get_size():
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 0))
    return overlay


def draw_front_arrows(screen, game, attack, size):
    color = game["nations"][attack["attacker"]]["color"]
    if attack["attacker"] == 0:
        color = PLAYER_ARROW_COLOR
    camera = game["camera"]
    for from_tile, to_tile in attack.get("arrows", []):
        start = tile_on_screen(from_tile, camera)
        end = tile_on_screen(to_tile, camera)
        # Push the tip a bit past the new tile, so the arrow is easy to see.
        end = (end[0] + (end[0] - start[0]) * 0.5, end[1] + (end[1] - start[1]) * 0.5)
        draw_arrow(screen, start, end, ARROW_SHADOW_COLOR, 5, size + 2)
        draw_arrow(screen, start, end, color, 3, size)


def draw_spearhead(screen, game, attack, zoom):
    camera = game["camera"]
    start = tile_on_screen(attack["start"], camera)
    tip = tile_on_screen(attack["tip"], camera)
    goal = tile_on_screen(attack["goal"], camera)
    width = max(2, int(zoom))
    pygame.draw.line(screen, SPEARHEAD_COLOR, start, tip, width)
    draw_dashed_line(screen, tip, goal, SPEARHEAD_COLOR, max(1, width // 2), 4)
    pygame.draw.circle(screen, ARROW_SHADOW_COLOR, goal, max(6, HEX_RADIUS * zoom * 1.4), 3)
    pygame.draw.circle(screen, SPEARHEAD_COLOR, goal, max(6, HEX_RADIUS * zoom * 1.4), 2)


def draw_feint(layer, game, attack, zoom):
    # A big, see-through, dashed arrow, so it looks like a large attack.
    if attack.get("start") is None:
        return
    camera = game["camera"]
    color = game["nations"][attack["attacker"]]["color"]
    start = tile_on_screen(attack["start"], camera)
    goal = tile_on_screen(attack["goal"], camera)
    # Make the arrow at least 8 tiles long, so it looks big even close to the border.
    dx, dy = goal[0] - start[0], goal[1] - start[1]
    length = max(0.001, (dx * dx + dy * dy) ** 0.5)
    least = 8 * HEX_WIDTH * zoom
    if length < least:
        start = (goal[0] - dx / length * least, goal[1] - dy / length * least)
    see_through = color + (150,)
    draw_dashed_line(layer, start, goal, see_through, max(3, int(2 * zoom)), 8)
    draw_arrow(layer, start, goal, see_through, 1, max(12, 5 * zoom))


def draw_dug_in(screen, game):
    camera = game["camera"]
    for tile, number in game.get("dug_in", {}).items():
        if owner_of(game, tile) != number:
            continue
        corners = [map_to_screen(corner, camera) for corner in hex_corners(*tile)]
        pygame.draw.polygon(screen, DUG_IN_COLOR, corners, 2)


def draw_scorched(layer, game):
    camera = game["camera"]
    for tile in game.get("scorched", {}):
        corners = [map_to_screen(corner, camera) for corner in hex_corners(*tile)]
        pygame.draw.polygon(layer, SCORCHED_COLOR, corners)


def draw_attacks(screen, game):
    # Draws arrows, spearheads and other attack marks on top of the map.
    zoom = game["camera"]["zoom"]
    arrow_size = max(7, 3 * zoom)
    draw_dug_in(screen, game)
    feints = [a for a in game["attacks"] if a.get("kind") == "feint"]
    if game.get("scorched") or feints:
        layer = get_overlay(screen)
        draw_scorched(layer, game)
        for attack in feints:
            draw_feint(layer, game, attack, zoom)
        screen.blit(layer, (0, 0))
    for attack in game["attacks"]:
        if attack.get("kind") == "spearhead":
            draw_spearhead(screen, game, attack, zoom)
        draw_front_arrows(screen, game, attack, arrow_size)
