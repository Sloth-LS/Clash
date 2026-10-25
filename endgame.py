import pygame

from settings import *
from widgets import Button
import audio
import menu
import theme
from nations import format_troops

WIN_PERCENT = 70          # you win when you own this much of all the land
VICTORY_COLOR = theme.AMBER
DEFEAT_COLOR = theme.RED
ELIMINATED_COLOR = (104, 106, 92)


# --- Checking if the game is over ---

def count_land(tiles):
    # Counts all land tiles on the map. This loops over the whole map,
    # so it is only done once and then kept in game["total_land"].
    total = 0
    for row in tiles:
        for tile in row:
            if tile == LAND:
                total += 1
    return total


def total_land(game):
    if "total_land" not in game:
        game["total_land"] = max(1, count_land(game["tiles"]))
    return game["total_land"]


def land_percent(game, nation):
    return 100 * len(nation["land"]) / total_land(game)


def update_stats(game):
    # Keeps the numbers for the game over screen up to date. Cheap enough for every frame.
    if "stats" not in game:
        game["stats"] = {"best_land_percent": 0, "peak_troops": 0, "time": 0, "eliminated": []}
    stats = game["stats"]
    you = game["nations"][0]
    stats["best_land_percent"] = max(stats["best_land_percent"], land_percent(game, you))
    stats["peak_troops"] = max(stats["peak_troops"], you["troops"])
    stats["time"] = game["time"]
    # Remember the order nations lose all their land in, for the ranking.
    for i, nation in enumerate(game["nations"]):
        if not nation["land"] and i not in stats["eliminated"]:
            stats["eliminated"].append(i)
    return stats


def check_game_over(game):
    # Returns "victory", "defeat" or None while the game goes on.
    started = game["spawn_timer"] is not None and game["spawn_timer"] <= 0
    if not started:
        return None
    update_stats(game)
    you = game["nations"][0]
    if not you["land"]:
        return "defeat"
    if land_percent(game, you) >= WIN_PERCENT:
        return "victory"
    for nation in game["nations"][1:]:
        if nation["land"]:
            return None  # a robot is still alive
    return "victory"


# --- The game over screen ---

def format_time(seconds):
    # 125 seconds becomes "2:05".
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


def ranking(game):
    # Returns the nation numbers, best first. Nations that are still alive come first
    # (most land first), then the eliminated ones (the last one to fall first).
    stats = game["stats"]
    alive = [i for i, nation in enumerate(game["nations"]) if nation["land"]]
    alive.sort(key=lambda i: len(game["nations"][i]["land"]), reverse=True)
    fallen = [i for i in reversed(stats["eliminated"]) if not game["nations"][i]["land"]]
    return alive + fallen


def draw_ranking(screen, game, font, left, right, top):
    # One row for every nation: place, color, name and land.
    # font is not used any more (the theme picks the fonts).
    for place, i in enumerate(ranking(game)):
        nation = game["nations"][i]
        y = top + place * 25
        if nation["land"]:
            color = MENU_TEXT_COLOR
            land_text = f"{land_percent(game, nation):.1f}%"
        else:
            color = ELIMINATED_COLOR
            land_text = "ELIMINATED"
        if i == 0:
            # Your own row gets an amber see-through stripe.
            row = pygame.Surface((right - left + 16, 23), pygame.SRCALPHA)
            row.fill((242, 164, 46, 40))
            screen.blit(row, (left - 8, y - 11))
            pygame.draw.rect(screen, theme.AMBER, (left - 8, y - 11, 3, 23))
            color = theme.AMBER if nation["land"] else color
        theme.blit_text(screen, "mono", 14, f"{place + 1:02d}", HINT_COLOR, midleft=(left + 2, y))
        pygame.draw.rect(screen, (0, 0, 0), (left + 32, y - 7, 14, 14))
        pygame.draw.rect(screen, nation["color"], (left + 34, y - 5, 10, 10))
        theme.blit_text(screen, "body", 16, nation["name"].upper(), color, midleft=(left + 58, y))
        if nation["land"]:
            theme.blit_text(screen, "mono", 15, land_text, color, midright=(right, y))
        else:
            theme.blit_text(screen, "body", 11, land_text, color, spacing=2, midright=(right, y))


def game_over_screen(screen, clock, game, result, options):
    # Shows who won and some numbers from the game. Returns "menu" or "quit".
    audio.stop_music()
    audio.play_sound(result)  # the sounds are called "victory" and "defeat"
    stats = update_stats(game)

    # The whole final map, darkened, behind a panel.
    behind = menu.darken(game["map_image"], 150)
    behind.blit(theme.make_grid_overlay(SCREEN_WIDTH, SCREEN_HEIGHT, alpha=0.7), (0, 0))
    panel = menu.make_panel(520, 594, "After action report")
    panel_rect = panel.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    center_x = panel_rect.centerx

    if result == "victory":
        title, title_color = "VICTORY", VICTORY_COLOR
        message = "The hex world is yours!"
        status = "MISSION COMPLETE"
    else:
        title, title_color = "DEFEAT", DEFEAT_COLOR
        message = "Your nation has fallen."
        status = "MISSION FAILED"
    you = game["nations"][0]
    numbers = [
        ("TIME PLAYED", format_time(stats["time"])),
        ("YOUR LAND", f"{land_percent(game, you):.1f}%"),
        ("MOST LAND", f"{stats['best_land_percent']:.1f}%"),
        ("MOST TROOPS", format_troops(stats["peak_troops"])),
    ]
    stripes = theme.hazard_stripes(panel_rect.width - 80, 5)

    # Two buttons next to each other. Enter picks the first one, Esc also goes to the menu.
    button_y = panel_rect.bottom - 84
    buttons = [Button((center_x - 210, button_y, 200, 48), "Main menu"),
               Button((center_x + 10, button_y, 200, 48), "Quit")]

    def draw_behind(screen):
        screen.blit(behind, (0, 0))
        screen.blit(panel, panel_rect)
        top = panel_rect.top
        theme.blit_text(screen, "body", 13, status, title_color, spacing=4, center=(center_x, top + 48))
        theme.blit_text(screen, "head", 78, title, title_color, spacing=8, shadow=True, center=(center_x, top + 96))
        screen.blit(stripes, (panel_rect.left + 40, top + 140))
        theme.blit_text(screen, "body", 17, message, MENU_TEXT_COLOR, center=(center_x, top + 162))

        # The numbers in two columns: a small label with the value below it.
        for i, (label, value) in enumerate(numbers):
            x = panel_rect.left + 50 + (i % 4) * 107
            theme.blit_text(screen, "body", 10, label, HINT_COLOR, spacing=2, topleft=(x, top + 188))
            theme.blit_text(screen, "mono", 20, value, MENU_TEXT_COLOR, topleft=(x, top + 203))

        tag = theme.draw_tag(screen, "Final ranking", panel_rect.left + 40, top + 248)
        pygame.draw.line(screen, (70, 76, 60), (tag.right + 8, top + 248),
                         (panel_rect.right - 40, top + 248))
        draw_ranking(screen, game, None, panel_rect.left + 48, panel_rect.right - 48, top + 276)
        theme.blit_text(screen, "body", 12, "ENTER OR ESC: MAIN MENU", HINT_COLOR, spacing=2,
                        center=(center_x, panel_rect.bottom - 20))

    choice = menu.run_button_menu(screen, clock, buttons, draw_behind, "Main menu")
    if choice == "Main menu":
        return "menu"
    return "quit"
