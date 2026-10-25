import random

from settings import *
from hexmap import neighbors_of
from nations import max_troops
import attacks

# --- Robot settings ---
# Every difficulty changes how the robots think and fight.
#   think:      a robot thinks once every this many seconds (lowest, highest)
#   percent:    part of its troops a robot sends in one attack
#   reserve:    a robot only attacks a nation when its troops are above this part of its max
#   strength:   multiplies ROBOT_STRENGTH, so the robots get a higher or lower max of troops
#   aggression: chance that a robot attacks a weak neighbor even when there is free land left
#   gang_up:    chance that a robot picks on you when you are the biggest nation
DIFFICULTIES = {
    "Easy": {"think": (2.0, 3.0), "percent": 0.25, "reserve": 0.6,
             "strength": 0.8, "aggression": 0.1, "gang_up": 0.1},
    "Normal": {"think": (1.5, 2.5), "percent": 0.35, "reserve": 0.5,
               "strength": 1.0, "aggression": 0.25, "gang_up": 0.35},
    "Hard": {"think": (1.0, 2.0), "percent": 0.45, "reserve": 0.4,
             "strength": 1.2, "aggression": 0.45, "gang_up": 0.6},
}
FREE_LAND_RESERVE = 0.2  # free land is cheap, so robots grab it with fewer troops
MIN_ATTACK_TROOPS = 40   # never send fewer troops than this (no tiny attacks)
MIN_TILES = 6            # an attack must be able to pay for at least this many tiles
MAX_ATTACKS = 2          # most attacks one robot runs at the same time
SMALL_NATION = 0.35      # a nation with less land than this part of ours is "small"
FINISH_BONUS = 2         # extra score for a nation we can (almost) finish off


def get_difficulty(game):
    name = game["setup"].get("difficulty", "Normal")
    return DIFFICULTIES.get(name, DIFFICULTIES["Normal"])


def set_up_robots(game):
    # Runs once, on the first update: gives every robot its strength and a think timer.
    difficulty = get_difficulty(game)
    high = difficulty["think"][1]
    for nation in game["nations"]:
        if nation["is_robot"]:
            nation["strength"] = ROBOT_STRENGTH * difficulty["strength"]
            nation["think_timer"] = random.uniform(0, high)  # so they don't all think at once
    game["robots_ready"] = True


def find_neighbors(game, i):
    # Goes once over nation i's land and counts the tiles that touch it, for every owner.
    # The result is like {None: 12, 3: 5}: 12 free tiles and 5 tiles of nation 3.
    tiles = game["tiles"]
    owners = game["owners"]
    seen = set()
    counts = {}
    for x, y in game["nations"][i]["land"]:
        for nx, ny in neighbors_of(x, y):
            if tiles[ny][nx] == LAND and (nx, ny) not in seen:
                owner = owners[ny][nx]
                if owner != i:
                    seen.add((nx, ny))
                    counts[owner] = counts.get(owner, 0) + 1
    return counts


def count_attacks(game, i):
    count = 0
    for attack in game["attacks"]:
        if attack["attacker"] == i:
            count += 1
    return count


def biggest_nation(nations):
    # Returns the number of the nation with the most land.
    best = 0
    for i, nation in enumerate(nations):
        if len(nation["land"]) > len(nations[best]["land"]):
            best = i
    return best


def tiles_we_can_take(enemy, troops_to_send):
    # About how many tiles troops_to_send can take from this nation.
    # This copies the idea of attacks.attack_cost: every tile costs more when the
    # enemy has many troops on each tile, or many more troops than we send.
    density = enemy["troops"] / max(1, len(enemy["land"]))
    ratio = min(max(enemy["troops"] / troops_to_send, 0.6), 2)
    return troops_to_send / (ratio * (ENEMY_TILE_COST + density))


def choose_target(game, i, neighbors, troops_to_send, difficulty):
    # Gives every neighbor nation a score and returns the best one (or None).
    nations = game["nations"]
    me = nations[i]
    gang_up = biggest_nation(nations) == 0 and random.random() < difficulty["gang_up"]
    best = None
    best_score = 0
    for target in neighbors:
        if target is None or target == i:
            continue
        enemy = nations[target]
        if not enemy["land"]:
            continue
        tiles = tiles_we_can_take(enemy, troops_to_send)
        share = min(1, tiles / len(enemy["land"]))  # how much of the enemy we could take
        if tiles < MIN_TILES and share < 0.5:
            continue  # we could hardly take anything, so don't bother
        # Weak nations (few troops on each tile) give the most tiles.
        # Nations we can almost finish off get a bonus.
        score = tiles * (1 + FINISH_BONUS * share)
        if len(enemy["land"]) < len(me["land"]) * SMALL_NATION:
            score *= 1.5
        if target == 0 and gang_up:
            score *= 3
        score *= random.uniform(0.8, 1.2)  # a little luck, so robots are not too predictable
        if score > best_score:
            best = target
            best_score = score
    return best


def robot_think(game, i, difficulty):
    # One robot decides if it wants to attack, and whom.
    me = game["nations"][i]
    if not me["land"] or count_attacks(game, i) >= MAX_ATTACKS:
        return
    fullness = me["troops"] / max_troops(me)
    troops_to_send = me["troops"] * difficulty["percent"]
    if troops_to_send < MIN_ATTACK_TROOPS:
        return
    neighbors = find_neighbors(game, i)

    # Sometimes a robot fights a neighbor even when there is free land.
    wants_fight = not neighbors.get(None) or random.random() < difficulty["aggression"]
    if wants_fight and fullness >= difficulty["reserve"]:
        target = choose_target(game, i, neighbors, troops_to_send, difficulty)
        if target is not None:
            attacks.start_attack(game, i, target, difficulty["percent"])
            return

    # Otherwise grab free land while there is some.
    if neighbors.get(None) and fullness >= FREE_LAND_RESERVE:
        attacks.start_attack(game, i, None, difficulty["percent"])


def update_robots(game, seconds):
    # Lets every robot nation think and attack. Called every frame while the game runs.
    if not game.get("robots_ready"):
        set_up_robots(game)
    difficulty = get_difficulty(game)
    low, high = difficulty["think"]
    for i, nation in enumerate(game["nations"]):
        if not nation["is_robot"] or not nation["land"]:
            continue  # you, or a robot that has lost all its land
        nation["think_timer"] -= seconds
        if nation["think_timer"] <= 0:
            nation["think_timer"] = random.uniform(low, high)
            robot_think(game, i, difficulty)
