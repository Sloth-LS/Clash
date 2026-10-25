import math

import pygame

from settings import *
from hexmap import hex_center, pixel_to_hex
from camera import map_to_screen, screen_to_map
from nations import max_troops, format_troops
import theme

# --- HUD settings ---
BAR_HEIGHT = 42                  # height of the bar at the bottom
PANEL_COLOR = (20, 24, 22, 228)  # dark gunmetal, a little see-through (the last number)
PANEL_EDGE_COLOR = theme.EDGE
TROOP_BAR_WIDTH = 96             # the small bar that shows how full your troops are
TROOP_BAR_COLOR = theme.GREEN
TROOP_BAR_BACK_COLOR = (12, 14, 14)
LEADERBOARD_SIZE = 5             # how many nations the leaderboard shows
LEADERBOARD_WIDTH = 262
ROW_HEIGHT_HUD = 22              # height of one line in the leaderboard and tooltip
HIGHLIGHT_COLOR = (242, 164, 46, 40)  # the see-through amber behind your own row
PAUSED_COLOR = theme.AMBER
PAUSED_DIM_COLOR = (0, 0, 0, 110)     # the see-through black over the map while paused

# Fonts can only be made after pygame.init(), so they are made the first time they are needed.
fonts = {}
# See-through panels are slow to make, so each size is only made once.
panels = {}


def get_font(size):
    if size not in fonts:
        fonts[size] = pygame.font.SysFont(None, size)
    return fonts[size]


def get_panel(width, height):
    # A dark see-through plate with cut corners and a thin olive edge.
    if (width, height) not in panels:
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        rect = panel.get_rect()
        cut = min(8, height // 4)
        pygame.draw.polygon(panel, PANEL_COLOR, theme.chamfer_points(rect, cut))
        theme.draw_scanlines(panel, theme.lighter(PANEL_COLOR, 5), rect.inflate(-4, -4))
        pygame.draw.polygon(panel, PANEL_EDGE_COLOR, theme.chamfer_points(rect, cut), 1)
        panels[(width, height)] = panel
    return panels[(width, height)]


def draw_label(screen, font, text, center):
    # Draws white text with a black outline, so it can be read on any color.
    # The theme picks the font, but font is kept so older code still works.
    label = theme.text("body", 13, text, MENU_TEXT_COLOR)
    shadow = theme.text("body", 13, text, (0, 0, 0))
    label_pos = label.get_rect(center=center)
    for dx, dy in ((1, 1), (-1, 0), (1, 0), (0, -1)):
        screen.blit(shadow, label_pos.move(dx, dy))
    screen.blit(label, label_pos)


def draw_text(screen, font, text, color, **position):
    # Draws text placed with any pygame.Rect position, like topleft=(10, 10) or midleft=(x, y).
    label = font.render(text, True, color)
    screen.blit(label, label.get_rect(**position))
    return label.get_rect(**position)


def draw_capital(screen, nation, center):
    # A capital: a small diamond in the nation's color, then its name and troops.
    x, y = center
    diamond = [(x, y - 4), (x + 4, y), (x, y + 4), (x - 4, y)]
    pygame.draw.polygon(screen, (0, 0, 0), [(px, py + 1) for px, py in diamond])
    pygame.draw.polygon(screen, nation["color"], diamond)
    pygame.draw.polygon(screen, (0, 0, 0), diamond, 1)
    name = nation["name"].upper()
    draw_label(screen, None, name, (x, y - 13))
    troops = theme.text("mono", 13, format_troops(nation["troops"]), theme.AMBER)
    shadow = theme.text("mono", 13, format_troops(nation["troops"]), (0, 0, 0))
    rect = troops.get_rect(center=(x, y + 12))
    for dx, dy in ((1, 1), (-1, 0), (1, 0), (0, -1)):
        screen.blit(shadow, rect.move(dx, dy))
    screen.blit(troops, rect)


def draw_nations(screen, nations, font, camera):
    for nation in nations:
        if nation["capital"] not in nation["land"]:
            continue  # no start picked yet, or the capital was taken
        x, y = nation["capital"]
        center = map_to_screen(hex_center(x, y), camera)
        draw_capital(screen, nation, (int(center[0]), int(center[1])))


def total_land(game):
    # How many land tiles the whole map has. Counted once, then kept in the game dict.
    if "total_land" not in game:
        count = 0
        for row in game["tiles"]:
            count += row.count(LAND)
        game["total_land"] = max(1, count)
    return game["total_land"]


def land_percent(game, nation):
    return 100 * len(nation["land"]) / total_land(game)


def format_time(seconds):
    # 125 seconds turns into "02:05".
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def has_started(game):
    # The same check as in clash.py (copied, so hud.py doesn't need to import clash.py).
    return game["spawn_timer"] is not None and game["spawn_timer"] <= 0


def get_bar():
    # The bottom bar: gunmetal with an amber line on top and small warning stripes on the left.
    if "bar" not in panels:
        bar = pygame.Surface((SCREEN_WIDTH, BAR_HEIGHT), pygame.SRCALPHA)
        bar.fill(PANEL_COLOR)
        theme.draw_scanlines(bar, theme.lighter(PANEL_COLOR, 5), bar.get_rect())
        pygame.draw.line(bar, theme.EDGE, (0, 0), (SCREEN_WIDTH, 0))
        pygame.draw.line(bar, theme.AMBER, (0, 0), (150, 0), 2)
        pygame.draw.line(bar, theme.AMBER, (SCREEN_WIDTH - 150, 0), (SCREEN_WIDTH, 0), 2)
        bar.blit(theme.hazard_stripes(6, BAR_HEIGHT - 2), (0, 2))
        panels["bar"] = bar
    return panels["bar"]


def draw_divider(screen, x, top):
    # A thin line between two parts of the bottom bar, with a small notch.
    pygame.draw.line(screen, (70, 76, 60), (x, top + 7), (x, top + BAR_HEIGHT - 7))
    pygame.draw.line(screen, theme.EDGE, (x - 2, top + 7), (x + 2, top + 7))


def draw_readout(screen, x, top, label, value, color=None):
    # A small stencil label with a number below it. Returns where the value ends.
    theme.blit_text(screen, "body", 11, label, theme.DIM, spacing=2, topleft=(x, top + 5))
    rect = theme.blit_text(screen, "mono", 17, value, color or theme.TEXT, topleft=(x, top + 19))
    return rect.right


def draw_bottom_bar(screen, game):
    # The bar at the bottom with your troops, land, attack percent, attacks and time.
    top = SCREEN_HEIGHT - BAR_HEIGHT
    middle = top + BAR_HEIGHT // 2
    screen.blit(get_bar(), (0, top))

    if not has_started(game):
        # Before the start you only need to know the keys.
        hints = theme.make_hint_line([("SPACE", "new map"), ("Q / E", "zoom"), ("T / Y", "attack %"),
                                      ("P", "pause"), ("ESC", "menu")])
        screen.blit(hints, hints.get_rect(center=(SCREEN_WIDTH // 2, middle + 1)))
        return

    you = game["nations"][0]
    troops = int(you["troops"])
    most = int(max_troops(you))

    # Troops with a small bar that fills up.
    x = 20
    right = draw_readout(screen, x, top, "FORCES", f"{format_troops(troops)} / {format_troops(most)}")
    back = pygame.Rect(right + 10, top + 25, TROOP_BAR_WIDTH, 8)
    pygame.draw.rect(screen, TROOP_BAR_BACK_COLOR, back)
    fill = back.copy()
    fill.width = int(TROOP_BAR_WIDTH * min(1, troops / max(1, most)))
    if fill.width > 0:
        pygame.draw.rect(screen, TROOP_BAR_COLOR, fill)
    # Ruler marks on the bar every quarter.
    for i in range(1, 4):
        mark_x = back.left + i * TROOP_BAR_WIDTH // 4
        pygame.draw.line(screen, (20, 24, 22), (mark_x, back.top), (mark_x, back.bottom - 1))
    pygame.draw.rect(screen, theme.EDGE, back, 1)
    x = back.right + 18
    draw_divider(screen, x, top)
    x += 16

    # Land.
    right = draw_readout(screen, x, top, "TERRITORY", f"{land_percent(game, you):.1f}%")
    x = max(right, x + 76) + 16
    draw_divider(screen, x, top)
    x += 16

    # Attack percent and how many troops one click sends.
    percent = game["attack_percent"]
    sends = int(you["troops"] * percent)
    theme.blit_text(screen, "body", 11, "ATTACK", theme.DIM, spacing=2, topleft=(x, top + 5))
    rect = theme.blit_text(screen, "mono", 17, f"{round(percent * 100)}%", theme.AMBER, topleft=(x, top + 19))
    rect = theme.blit_text(screen, "mono", 14, f"= {format_troops(sends)}", theme.DIM,
                           bottomleft=(rect.right + 6, rect.bottom - 1))
    cap = theme.keycap("T/Y", 11)
    screen.blit(cap, cap.get_rect(midleft=(rect.right + 10, rect.centery)))
    x = max(rect.right + 10 + cap.get_width(), x + 100) + 16
    draw_divider(screen, x, top)
    x += 16

    # Your attacks that are moving right now.
    running = 0
    for attack in game["attacks"]:
        if attack["attacker"] == 0:
            running += 1
    color = theme.AMBER if running else theme.TEXT
    right = draw_readout(screen, x, top, "OPERATIONS", f"{running} ACTIVE", color)
    if running and theme.blink(0.8):
        pygame.draw.circle(screen, theme.AMBER, (right + 10, top + 27), 3)

    # Game time in the right corner.
    clock_rect = theme.blit_text(screen, "mono", 20, format_time(game["time"]), theme.TEXT,
                                 midright=(SCREEN_WIDTH - 18, top + 26))
    theme.blit_text(screen, "body", 11, "MISSION TIME", theme.DIM, spacing=2,
                    topright=(SCREEN_WIDTH - 18, top + 5))
    theme.blit_text(screen, "mono", 14, "T+", theme.AMBER, midright=(clock_rect.left - 5, clock_rect.centery + 1))


def draw_leaderboard(screen, game):
    # The top nations by land in the top right corner. Returns its box (for the tooltip).
    nations = game["nations"]
    alive = [i for i in range(len(nations)) if nations[i]["land"]]
    alive.sort(key=lambda i: len(nations[i]["land"]), reverse=True)
    shown = alive[:LEADERBOARD_SIZE]
    # If you are not in the top 5, you still get your own line at the bottom.
    if 0 in alive and 0 not in shown:
        shown.append(0)

    header = 26
    height = header + 18 + ROW_HEIGHT_HUD * len(shown) + 8
    left = SCREEN_WIDTH - LEADERBOARD_WIDTH - 8
    top = 8
    right = left + LEADERBOARD_WIDTH
    screen.blit(get_panel(LEADERBOARD_WIDTH, height), (left, top))
    # The header strip.
    pygame.draw.line(screen, theme.EDGE, (left + 1, top + header), (right - 2, top + header))
    pygame.draw.rect(screen, theme.AMBER, (left + 12, top + 8, 5, 10))
    theme.blit_text(screen, "body", 13, "SITREP", theme.KHAKI, spacing=3, midleft=(left + 24, top + 13))
    theme.blit_text(screen, "mono", 12, f"{len(alive)} NATIONS", theme.DIM, midright=(right - 12, top + 14))
    # Column names.
    column_y = top + header + 10
    theme.blit_text(screen, "body", 10, "NATION", theme.DIM, spacing=2, midleft=(left + 40, column_y))
    theme.blit_text(screen, "body", 10, "LAND", theme.DIM, spacing=2, midright=(left + 194, column_y))
    theme.blit_text(screen, "body", 10, "TROOPS", theme.DIM, spacing=2, midright=(right - 12, column_y))

    y = top + header + 18
    for i in shown:
        nation = nations[i]
        row_middle = y + ROW_HEIGHT_HUD // 2
        if i == 0:
            if "highlight" not in panels:
                panels["highlight"] = pygame.Surface((LEADERBOARD_WIDTH - 4, ROW_HEIGHT_HUD), pygame.SRCALPHA)
                panels["highlight"].fill(HIGHLIGHT_COLOR)
            screen.blit(panels["highlight"], (left + 2, y))
            pygame.draw.rect(screen, theme.AMBER, (left + 2, y, 3, ROW_HEIGHT_HUD))
        rank = alive.index(i) + 1
        name_color = theme.AMBER if i == 0 else theme.TEXT
        theme.blit_text(screen, "mono", 13, f"{rank:02d}", theme.DIM, midleft=(left + 10, row_middle))
        chip = pygame.Rect(left + 31, row_middle - 5, 10, 10)
        pygame.draw.rect(screen, (0, 0, 0), chip.inflate(2, 2))
        pygame.draw.rect(screen, nation["color"], chip)
        theme.blit_text(screen, "body", 13, nation["name"].upper(), name_color, midleft=(left + 48, row_middle))
        theme.blit_text(screen, "mono", 14, f"{land_percent(game, nation):.1f}%", theme.TEXT,
                        midright=(left + 194, row_middle))
        theme.blit_text(screen, "mono", 14, format_troops(nation["troops"]), theme.TEXT,
                        midright=(right - 12, row_middle))
        y += ROW_HEIGHT_HUD
    return pygame.Rect(left, top, LEADERBOARD_WIDTH, height)


def draw_tooltip(screen, game, blocked):
    # Shows the name, troops and land of the nation under the mouse.
    # blocked is a list of boxes (HUD panels) where no tooltip should show.
    mouse = pygame.mouse.get_pos()
    if not pygame.mouse.get_focused():
        return
    for box in blocked:
        if box.collidepoint(mouse):
            return
    tile = pixel_to_hex(*screen_to_map(mouse, game["camera"]))
    if tile is None:
        return
    owner = game["owners"][tile[1]][tile[0]]
    if owner is None:
        return
    nation = game["nations"][owner]

    name = theme.text("body", 15, nation["name"].upper(), theme.TEXT, spacing=1)
    tag = "YOU" if owner == 0 else "HOSTILE"
    tag_label = theme.text("body", 10, tag, theme.AMBER if owner == 0 else theme.RED, spacing=2)
    lines = [("TROOPS", format_troops(nation["troops"])), ("LAND", f"{len(nation['land'])} tiles")]
    width = max(name.get_width() + tag_label.get_width() + 40, 170)
    height = 30 + ROW_HEIGHT_HUD * len(lines) + 4

    # Next to the mouse, but flipped to the other side near the edge of the screen.
    x = mouse[0] + 18
    y = mouse[1] + 18
    if x + width > SCREEN_WIDTH:
        x = mouse[0] - 18 - width
    if y + height > SCREEN_HEIGHT - BAR_HEIGHT:
        y = mouse[1] - 18 - height
    screen.blit(get_panel(width, height), (x, y))

    # A stripe in the nation's color, then the name and a small tag.
    pygame.draw.rect(screen, nation["color"], (x + 3, y + 6, 4, height - 12))
    screen.blit(name, name.get_rect(midleft=(x + 15, y + 15)))
    screen.blit(tag_label, tag_label.get_rect(midright=(x + width - 12, y + 15)))
    pygame.draw.line(screen, (70, 76, 60), (x + 15, y + 28), (x + width - 12, y + 28))
    row_middle = y + 30 + ROW_HEIGHT_HUD // 2
    for label, value in lines:
        theme.blit_text(screen, "body", 11, label, theme.DIM, spacing=2, midleft=(x + 15, row_middle))
        theme.blit_text(screen, "mono", 15, value, theme.TEXT, midright=(x + width - 12, row_middle))
        row_middle += ROW_HEIGHT_HUD
    theme.draw_brackets(screen, pygame.Rect(x - 3, y - 3, width + 6, height + 6), theme.AMBER, length=6, width=1)


def draw_paused(screen):
    # A stamp that says PAUSED in the middle of the screen.
    center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20)
    if "paused" not in panels:
        stamp = pygame.Surface((360, 150), pygame.SRCALPHA)
        rect = stamp.get_rect()
        pygame.draw.polygon(stamp, (20, 24, 22, 220), theme.chamfer_points(rect, 14))
        pygame.draw.polygon(stamp, theme.AMBER, theme.chamfer_points(rect, 14), 2)
        pygame.draw.polygon(stamp, theme.AMBER_DIM, theme.chamfer_points(rect.inflate(-12, -12), 10), 1)
        label = theme.text("head", 76, "PAUSED", PAUSED_COLOR, spacing=8)
        stamp.blit(label, label.get_rect(center=(180, 62)))
        stamp.blit(theme.hazard_stripes(240, 5), (60, 112))
        hint = theme.text("body", 13, "PRESS P TO RESUME", theme.KHAKI, spacing=3)
        stamp.blit(hint, hint.get_rect(center=(180, 131)))
        panels["paused"] = stamp
    stamp = panels["paused"]
    screen.blit(stamp, stamp.get_rect(center=center))


def draw_hud(screen, game):
    # Draws the bar with your troops, land and attack percent, the leaderboard,
    # the tooltip under the mouse and "PAUSED". Runs every frame.
    if game["paused"]:
        # Make the map a bit darker first, so the HUD on top stays bright.
        if "dim" not in panels:
            panels["dim"] = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            panels["dim"].fill(PAUSED_DIM_COLOR)
        screen.blit(panels["dim"], (0, 0))
    bar = pygame.Rect(0, SCREEN_HEIGHT - BAR_HEIGHT, SCREEN_WIDTH, BAR_HEIGHT)
    blocked = [bar]
    if has_started(game):
        blocked.append(draw_leaderboard(screen, game))
    draw_bottom_bar(screen, game)
    draw_tooltip(screen, game, blocked)
    if game["paused"]:
        draw_paused(screen)


def draw_spawn_message(screen, font, spawn_timer):
    # A plate at the top that tells you to pick a start spot, then counts down.
    if spawn_timer is None:
        tag = "DEPLOY"
        text = "Click on land to choose where you start"
    elif spawn_timer > 0:
        tag = f"T-{math.ceil(spawn_timer):02d}"
        text = "Deploying... click again to move"
    else:
        return
    width, height = 470, 40
    rect = pygame.Rect(0, 0, width, height)
    rect.midtop = (SCREEN_WIDTH // 2, 12)
    screen.blit(get_panel(width, height), rect)
    tag_box = pygame.Rect(rect.left + 8, rect.top + 8, 70, height - 16)
    pygame.draw.polygon(screen, theme.AMBER, theme.chamfer_points(tag_box, 5, 0))
    theme.blit_text(screen, "mono", 15, tag, (20, 18, 12), center=tag_box.center)
    theme.blit_text(screen, "body", 17, text, theme.TEXT, midleft=(tag_box.right + 14, rect.centery))
    if theme.blink(1.0):
        pygame.draw.circle(screen, theme.AMBER, (rect.right - 16, rect.centery), 4)
