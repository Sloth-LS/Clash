import json
import os
import sys

import pygame

from settings import *
from widgets import Button, Slider
import audio
import theme



def game_folder():
    # The folder where the game keeps its files.
    # As a PyInstaller .exe, __file__ points into a temporary folder that is deleted
    # when the game closes, so we use the folder the .exe is in instead.
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def options_file():
    return os.path.join(game_folder(), "options.json")


# Every option and what it is before the player changes anything.
DEFAULT_OPTIONS = {
    "music_volume": 0.5,  # 0 is silent, 1 is full volume
    "sound_volume": 0.7,
    "fullscreen": False,
    "show_fps": False,
}

# The keys shown on the "Controls" page: (key, what it does).
CONTROLS = [
    ("W A S D / Arrows", "Move the camera"),
    ("Mouse wheel / Q E", "Zoom in and out"),
    ("C", "Center on your capital"),
    ("P", "Pause"),
    ("T / Y", "Attack percent -/+ 10"),
    ("Space", "New map (before start)"),
    ("Esc", "Pause menu"),
    ("Left click", "Start spot / attack"),
    ("Shift + click", "Attack with double troops"),
    ("Double click", "Spearhead"),
    ("Ctrl + click", "Feint"),
    ("Right click enemy", "Stop the attack"),
    ("Right click own border", "Dig in"),
    ("Hold R + click own land", "Scorched earth"),
]
CONTROLS_PER_COLUMN = 7  # the Controls page shows the list in two columns


def load():
    # Reads options.json. Missing or broken files just give the default options.
    # Old files that miss some options get the default for those.
    options = dict(DEFAULT_OPTIONS)
    try:
        with open(options_file()) as file:
            saved = json.load(file)
    except (OSError, ValueError):
        return options
    if not isinstance(saved, dict):
        return options
    for name in DEFAULT_OPTIONS:
        # Only keep a saved value if it is the same kind of thing as the default.
        if name in saved and type(saved[name]) in (type(DEFAULT_OPTIONS[name]), int):
            options[name] = saved[name]
    # Volumes must stay between 0 and 1.
    for name in ("music_volume", "sound_volume"):
        options[name] = max(0, min(1, float(options[name])))
    options["fullscreen"] = bool(options["fullscreen"])
    options["show_fps"] = bool(options["show_fps"])
    return options


def save(options):
    try:
        with open(options_file(), "w") as file:
            json.dump(options, file, indent=4)
    except OSError:
        pass  # not being able to save should not crash the game


def make_screen(options):
    # Opens (or reopens) the game window, in fullscreen if that option is on.
    flags = pygame.SCALED
    if options["fullscreen"]:
        flags |= pygame.FULLSCREEN
    return pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)


def on_off(value):
    # Text for a toggle button.
    return "On" if value else "Off"


def draw_text(screen, font, text, color, **position):
    # Draws text. position is e.g. center=(x, y) or midleft=(x, y).
    label = font.render(text, True, color)
    screen.blit(label, label.get_rect(**position))


def draw_controls(screen, font):
    # Draws the CONTROLS list in two columns: the keys in amber, what they do in white.
    # font is not used any more (the theme picks the fonts).
    column_width = (SCREEN_WIDTH - 104) // 2
    for column in range(2):
        rows = CONTROLS[column * CONTROLS_PER_COLUMN:(column + 1) * CONTROLS_PER_COLUMN]
        left = 60 + column * column_width
        # The actions start right after the widest key in this column.
        key_width = max(theme.font("mono", 15).size(key.upper())[0] for key, action in rows)
        y = 222
        for key, action in rows:
            row = pygame.Rect(left - 8, y - 16, column_width - 12, 32)
            pygame.draw.rect(screen, (26, 30, 27), row)
            pygame.draw.rect(screen, theme.AMBER_DIM, (row.left, row.top, 3, row.height))
            theme.blit_text(screen, "mono", 15, key.upper(), SLIDER_KNOB_COLOR, midleft=(left + 4, y))
            theme.blit_text(screen, "body", 16, action, MENU_TEXT_COLOR, midleft=(left + key_width + 20, y))
            y += 38


def options_screen(screen, clock, options):
    # Lets the player change the options. Saves them and returns the (changed) options.
    font = pygame.font.SysFont(None, 32)
    small_font = pygame.font.SysFont(None, 26)
    center_x = SCREEN_WIDTH // 2
    label_x = 76                 # where the row names start
    control_x = 440              # where sliders and buttons start
    panel_rect = pygame.Rect(24, 18, SCREEN_WIDTH - 48, SCREEN_HEIGHT - 36)
    panel = theme.make_plate(panel_rect.width, panel_rect.height, "Command console")
    hints = theme.make_hint_line([("ESC", "back"), ("DRAG", "change a slider")])

    # Two pages: "settings" and "controls".
    page = "settings"
    settings_tab = Button((SCREEN_WIDTH - 380, 76, 150, 40), "Settings")
    controls_tab = Button((SCREEN_WIDTH - 220, 76, 150, 40), "Controls")

    # Rows on the settings page.
    music_y = 208
    sound_y = 278
    fullscreen_y = 368
    fps_y = 438
    music_slider = Slider((control_x, music_y - 4, 300, 8), 0, 100,
                          round(options["music_volume"] * 100), whole_numbers=True)
    sound_slider = Slider((control_x, sound_y - 4, 300, 8), 0, 100,
                          round(options["sound_volume"] * 100), whole_numbers=True)
    fullscreen_button = Button((control_x, fullscreen_y - 22, 120, 44), on_off(options["fullscreen"]))
    fps_button = Button((control_x, fps_y - 22, 120, 44), on_off(options["show_fps"]))

    back_button = Button((center_x - 110, SCREEN_HEIGHT - 116, 220, 50), "Back")

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Save, then put the QUIT back so the caller also quits.
                save(options)
                pygame.event.post(pygame.event.Event(pygame.QUIT))
                return options
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                save(options)
                return options
            elif back_button.is_clicked(event):
                audio.play_sound("menu_select")
                save(options)
                return options
            elif settings_tab.is_clicked(event):
                audio.play_sound("menu_select")
                page = "settings"
            elif controls_tab.is_clicked(event):
                audio.play_sound("menu_select")
                page = "controls"
            elif page == "settings":
                if fullscreen_button.is_clicked(event):
                    audio.play_sound("menu_select")
                    options["fullscreen"] = not options["fullscreen"]
                    fullscreen_button.text = on_off(options["fullscreen"])
                    make_screen(options)
                    screen = pygame.display.get_surface()
                elif fps_button.is_clicked(event):
                    audio.play_sound("menu_select")
                    options["show_fps"] = not options["show_fps"]
                    fps_button.text = on_off(options["show_fps"])
                else:
                    if music_slider.handle_event(event):
                        options["music_volume"] = music_slider.value / 100
                        audio.apply_volumes(options)
                    was_dragging = sound_slider.dragging
                    if sound_slider.handle_event(event):
                        options["sound_volume"] = sound_slider.value / 100
                        audio.apply_volumes(options)
                    if was_dragging and not sound_slider.dragging:
                        audio.play_sound("click")  # let the player hear the new volume

        theme.draw_backdrop(screen)
        screen.blit(panel, panel_rect)
        theme.blit_text(screen, "body", 13, "SYSTEM // CONFIG", theme.AMBER, spacing=3, bottomleft=(58, 66))
        theme.blit_text(screen, "head", 42, "OPTIONS", MENU_TEXT_COLOR, spacing=2, shadow=True, topleft=(56, 66))
        # The tab of the page we are on lights up and gets an amber line under it.
        settings_tab.draw(screen, font, page == "settings")
        controls_tab.draw(screen, font, page == "controls")
        current_tab = settings_tab if page == "settings" else controls_tab
        pygame.draw.line(screen, SLIDER_KNOB_COLOR, (current_tab.rect.left + 10, current_tab.rect.bottom + 8),
                         (current_tab.rect.right - 10, current_tab.rect.bottom + 8), 3)
        theme.draw_divider(screen, 56, SCREEN_WIDTH - 56, 140)

        if page == "settings":
            rows = [("Audio", "Music volume", music_y), ("Audio", "Sound volume", sound_y),
                    ("Display", "Fullscreen", fullscreen_y), ("Display", "Show FPS", fps_y)]
            for tag, name, y in rows:
                theme.draw_tag(screen, tag, label_x, y)
                theme.blit_text(screen, "body", 20, name, MENU_TEXT_COLOR, midleft=(label_x + 96, y))
            pygame.draw.line(screen, (70, 76, 60), (label_x, 323), (SCREEN_WIDTH - 76, 323))
            music_slider.draw(screen)
            theme.blit_text(screen, "mono", 20, f"{music_slider.value:3d}%", SLIDER_KNOB_COLOR,
                            midleft=(music_slider.rect.right + 28, music_y))
            sound_slider.draw(screen)
            theme.blit_text(screen, "mono", 20, f"{sound_slider.value:3d}%", SLIDER_KNOB_COLOR,
                            midleft=(sound_slider.rect.right + 28, sound_y))
            fullscreen_button.draw(screen, font)
            fps_button.draw(screen, font)
        else:
            draw_controls(screen, small_font)

        back_button.draw(screen, font)
        screen.blit(hints, hints.get_rect(center=(center_x, SCREEN_HEIGHT - 44)))

        pygame.display.flip()
        clock.tick(FPS)
