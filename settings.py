import math

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
SPAWN_TIME = 10       # seconds you have to move your start after your first pick
START_TROOPS = 200    # troops every nation starts with
TROOP_BASE = 500      # max troops a nation can have with no land
TROOPS_PER_LAND = 100 # how much land raises the max troops
TROOP_GROWTH = 10     # troops per second you always get (before the slowdown)
ROBOT_STRENGTH = 0.75 # robots can only reach this part of the max troops
MIN_GROWTH_PART = 0.1 # close to the max, troops still grow at least this part of normal speed
FPS = 60              # frames per second
ATTACK_PERCENT = 0.2  # part of your troops one click sends (0.2 = 20 %)
ATTACK_STEP = 0.1     # seconds between each time the attacks move
FREE_TILE_COST = 1    # troops it costs to take one free land tile
ENEMY_TILE_COST = 2   # troops it costs to take one enemy tile (before the defenders count)
FREE_LAND_SPEED = 0.3 # part of the front taken each step on free land
ENEMY_LAND_SPEED = 0.15 # part of the front taken each step on enemy land

# --- Hexagon measurements ---
HEX_WIDTH = math.sqrt(3) * HEX_RADIUS   # width of one hexagon
ROW_HEIGHT = 1.5 * HEX_RADIUS           # how far down each new row starts
SCREEN_WIDTH = int(MAP_WIDTH * HEX_WIDTH + HEX_WIDTH / 2) + 1
SCREEN_HEIGHT = int(MAP_HEIGHT * ROW_HEIGHT + HEX_RADIUS / 2) + 1

# --- Tile types ---
WATER = 0
LAND = 1

# --- Colors (red, green, blue) ---
# A muted "war table" palette: olive land, dark slate water, amber highlights.
WATER_COLOR = (38, 56, 64)
LAND_COLOR = (116, 120, 84)
WATER_EDGE_COLOR = (33, 49, 56)
LAND_EDGE_COLOR = (102, 106, 74)
SELECTED_COLOR = (242, 164, 46)
MENU_BACKGROUND = (20, 24, 25)
MENU_TEXT_COLOR = (230, 225, 205)
HINT_COLOR = (138, 142, 118)
SLIDER_TRACK_COLOR = (12, 14, 14)
SLIDER_KNOB_COLOR = (242, 164, 46)

# --- Nation colors ---
# The first color is yours, the rest go to the robots.
NATION_COLORS = [
    (250, 246, 232),  # you
    (212, 58, 48),    # red
    (238, 150, 36),   # orange
    (150, 92, 206),   # purple
    (52, 196, 190),   # cyan
    (232, 104, 168),  # pink
    (128, 84, 44),    # brown
    (22, 22, 22),     # black
]

# --- Neighbor directions ---
# Odd rows are pushed half a hexagon to the right,
# so even and odd rows have different neighbors.
EVEN_ROW_NEIGHBORS = [(-1, 0), (1, 0), (-1, -1), (0, -1), (-1, 1), (0, 1)]
ODD_ROW_NEIGHBORS = [(-1, 0), (1, 0), (0, -1), (1, -1), (0, 1), (1, 1)]
