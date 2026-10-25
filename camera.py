import pygame

from settings import *


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


def zoom_at_center(camera, steps):
    # Zoom in or out around the middle of the screen (used by the Q and E keys).
    zoom_camera(camera, (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2), steps)


def center_camera_on(camera, map_pos):
    # Moves the camera so the map point map_pos is in the middle of the screen.
    camera["x"] = map_pos[0] - SCREEN_WIDTH / 2 / camera["zoom"]
    camera["y"] = map_pos[1] - SCREEN_HEIGHT / 2 / camera["zoom"]
    clamp_camera(camera)


def draw_view(screen, map_image, camera):
    # Cut out the part of the map the camera sees and stretch it over the whole screen.
    view = pygame.Rect(int(camera["x"]), int(camera["y"]),
                       int(SCREEN_WIDTH / camera["zoom"]), int(SCREEN_HEIGHT / camera["zoom"]))
    part = map_image.subsurface(view)
    screen.blit(pygame.transform.scale(part, (SCREEN_WIDTH, SCREEN_HEIGHT)), (0, 0))
