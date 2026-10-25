import pygame

from settings import *
from hexmap import hex_center
from camera import zoom_at_center, center_camera_on

# --- Control settings ---
PERCENT_STEP = 0.1    # how much T and Y change the attack percent (0.1 = 10 percentage points)
MIN_PERCENT = 0.1     # the smallest attack percent (10 %)
MAX_PERCENT = 1.0     # the biggest attack percent (100 %)


def change_attack_percent(game, change):
    # Makes the attack percent bigger or smaller, but keeps it between MIN and MAX.
    percent = game["attack_percent"] + change
    percent = round(percent * 10) / 10  # stops numbers like 0.30000000004
    game["attack_percent"] = max(MIN_PERCENT, min(MAX_PERCENT, percent))


def center_on_capital(game):
    # Moves the camera to your capital. Does nothing if you haven't picked a start yet.
    you = game["nations"][0]
    if you["capital"] is None:
        return
    center_camera_on(game["camera"], hex_center(*you["capital"]))


def handle_key(game, event):
    # Keys pressed during a game (Esc and Space are handled in clash.py,
    # WASD and the arrow keys are read every frame in camera.move_camera).
    if event.key == pygame.K_t:
        change_attack_percent(game, -PERCENT_STEP)
    elif event.key == pygame.K_y:
        change_attack_percent(game, PERCENT_STEP)
    elif event.key == pygame.K_q:
        zoom_at_center(game["camera"], -1)
    elif event.key == pygame.K_e:
        zoom_at_center(game["camera"], 1)
    elif event.key == pygame.K_c:
        center_on_capital(game)
    elif event.key == pygame.K_p:
        game["paused"] = not game["paused"]
