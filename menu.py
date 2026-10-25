import math
import random

import pygame

from settings import *
from hexmap import neighbors_of, draw_map
from nations import make_nations, paint_tile
from widgets import Button, Slider
import audio
import maps
import options as options_module
import theme

VERSION = "v0.5"
TITLE_COLOR = theme.AMBER
TITLE_OUTLINE_COLOR = (28, 22, 12)
PANEL_COLOR = theme.PLATE + (232,)    # the last number is how see-through it is
PANEL_EDGE_COLOR = theme.EDGE
FOCUS_COLOR = theme.AMBER             # the button the keyboard picks lights up in this color
BACKGROUND_ZOOM = 1.3                 # how much bigger than the screen the menu map is
BLOB_SIZE = 6                         # how many rings of land each menu nation gets
DIFFICULTIES = ["Easy", "Normal", "Hard"]
DIFFICULTY_COLORS = [theme.GREEN, theme.AMBER, theme.RED]
DIFFICULTY_NOTES = ["Slow robots, low threat", "A fair fight", "Fast, aggressive robots"]
START_DIFFICULTY = 1                  # Normal

# The short rules on the "How to play" screen. An empty line makes a small gap.
RULES = [
    "Click on land to pick where you start.",
    "You can move it until the countdown ends.",
    "",
    "Your troops grow by themselves.",
    "More land gives you more troops.",
    "",
    "Click free land or an enemy to attack.",
    "Enemy land costs more troops than free land,",
    "and a big army beats a small one.",
    "",
    "Win: own 70 % of all land,",
    "or take every robot's last tile.",
    "Lose: lose all of your land.",
]

CREDITS = [
    "Made by Lauge for Hack Club Terra",
    "Inspired by OpenFront.io",
    "Music and sounds made in Python",
    "Built with pygame-ce",
]
# A small label in front of every credits line.
CREDIT_LABELS = ["Command", "Intel", "Signals", "Engineering"]

# Makes the seeds for new maps. It has its own random numbers,
# so making a map (which sets the normal random seed) can't change the next seed.
seed_maker = random.Random()


# --- Small drawing helpers ---

def draw_text(screen, font, text, color, center, shadow=True):
    # Draws text centered on a point, with a dark shadow so it is easy to read.
    label = font.render(text, True, color)
    rect = label.get_rect(center=center)
    if shadow:
        screen.blit(font.render(text, True, theme.EDGE_DARK), rect.move(1, 2))
    screen.blit(label, rect)


def make_panel(width, height, title=None):
    # A metal plate with cut corners and rivets for the menus to sit on.
    # title puts a small stencil label in a strip at the top.
    return theme.make_plate(width, height, title)


def draw_heading(screen, words, label, x, y):
    # A big stencil heading with a small amber label above it, like "OPERATION" over "NEW GAME".
    theme.blit_text(screen, "body", 13, label.upper(), theme.AMBER, spacing=3, bottomleft=(x + 2, y))
    return theme.blit_text(screen, "head", 38, words.upper(), theme.TEXT, spacing=2, shadow=True,
                           topleft=(x, y))


def darken(image, amount):
    # Returns a darker copy of a picture. amount 0 changes nothing, 255 is black.
    dark = image.copy()
    shade = pygame.Surface(dark.get_size(), pygame.SRCALPHA)
    shade.fill((0, 0, 0, amount))
    dark.blit(shade, (0, 0))
    return dark


def make_icon():
    # Draws the small hexagon picture for the window icon, so no image file is needed.
    icon = pygame.Surface((32, 32), pygame.SRCALPHA)
    for radius, color in ((16, TITLE_OUTLINE_COLOR), (13, TITLE_COLOR), (6, theme.PLATE)):
        corners = []
        for i in range(6):
            angle = math.radians(60 * i - 30)
            corners.append((16 + radius * math.cos(angle), 16 + radius * math.sin(angle)))
        pygame.draw.polygon(icon, color, corners)
    return icon


# --- The moving map behind the menus ---

def grow_blob(tiles, owners, nations, i, map_image):
    # Paints the land around nation number i's capital, a few rings out.
    nation = nations[i]
    edge = [nation["capital"]]
    for _ in range(BLOB_SIZE):
        new_edge = []
        for x, y in edge:
            for nx, ny in neighbors_of(x, y):
                if tiles[ny][nx] == LAND and owners[ny][nx] is None:
                    owners[ny][nx] = i
                    paint_tile(map_image, (nx, ny), nation)
                    new_edge.append((nx, ny))
        edge = new_edge


def make_background():
    # Draws a random map with some robot nations on it, once.
    # Every frame only moves this finished picture around, so the menu stays fast.
    tiles = maps.make_map(maps.MAP_TYPES[0])
    map_image = draw_map(tiles)
    nations = make_nations(tiles, 5)
    owners = [[None] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
    for i in range(1, len(nations)):  # number 0 is you, and you have no capital yet
        grow_blob(tiles, owners, nations, i, map_image)
    size = (int(SCREEN_WIDTH * BACKGROUND_ZOOM), int(SCREEN_HEIGHT * BACKGROUND_ZOOM))
    big_map = pygame.transform.smoothscale(map_image, size)
    return darken(big_map, 140)


def draw_background(screen, background):
    # Slowly drifts the camera back and forth over the background map,
    # with a grid, scan lines and a turning radar line on top.
    seconds = pygame.time.get_ticks() / 1000
    spare_x = background.get_width() - SCREEN_WIDTH
    spare_y = background.get_height() - SCREEN_HEIGHT
    x = spare_x / 2 + spare_x / 2 * math.sin(seconds * 0.05)
    y = spare_y / 2 + spare_y / 2 * math.sin(seconds * 0.037)
    screen.blit(background, (0, 0), (int(x), int(y), SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(theme.make_grid_overlay(SCREEN_WIDTH, SCREEN_HEIGHT), (0, 0))
    theme.draw_sweep(screen)


# --- The big title ---

def spaced_render(font, text, color, spacing):
    # Renders text with extra space between the letters.
    letters = [font.render(letter, True, color) for letter in text]
    width = sum(letter.get_width() for letter in letters) + spacing * (len(letters) - 1)
    surface = pygame.Surface((width, font.get_height()), pygame.SRCALPHA)
    x = 0
    for letter in letters:
        surface.blit(letter, (x, 0))
        x += letter.get_width() + spacing
    return surface


def make_title(font, text):
    # Renders the title once: amber stencil letters with a dark outline and a drop shadow.
    # Thin see-through cuts go through the letters, like the bridges of a stencil.
    label = spaced_render(font, text, TITLE_COLOR, 12)
    outline = spaced_render(font, text, TITLE_OUTLINE_COLOR, 12)
    border = 4
    width = label.get_width() + border * 2 + 10
    height = label.get_height() + border * 2 + 10
    title = pygame.Surface((width, height), pygame.SRCALPHA)
    shadow = spaced_render(font, text, (0, 0, 0), 12)
    shadow.set_alpha(150)
    title.blit(shadow, (border + 8, border + 9))
    for dx in range(-border, border + 1, 2):
        for dy in range(-border, border + 1, 2):
            title.blit(outline, (border + dx, border + dy))
    title.blit(label, (border, border))
    # The lower half a bit darker, like light falling on painted metal.
    lower = pygame.Surface((width, height), pygame.SRCALPHA)
    lower.fill((255, 255, 255, 255))
    pygame.draw.rect(lower, (225, 200, 175, 255), (0, height // 2 + 6, width, height))
    title.blit(lower, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    # The stencil cuts.
    for cut_y in (int(height * 0.45), int(height * 0.60)):
        pygame.draw.rect(title, (0, 0, 0, 0), (0, cut_y, width, 3))
    return title


def draw_title(screen, title, center):
    # The title stays still (it is a stencil on metal), with ruler lines on both sides.
    rect = title.get_rect(center=center)
    screen.blit(title, rect)
    y = rect.bottom - 14
    for side in (-1, 1):
        start = center[0] + side * (rect.width // 2 + 10)
        end = start + side * 170
        pygame.draw.line(screen, theme.EDGE, (start, y), (end, y))
        for i in range(18):
            x = start + side * i * 10
            pygame.draw.line(screen, theme.EDGE, (x, y), (x, y - (7 if i % 5 == 0 else 3)))


# --- Buttons ---

def hovered_index(buttons):
    # Returns the number of the button under the mouse, or None.
    for i, button in enumerate(buttons):
        if button.is_hovered():
            return i
    return None


def draw_buttons(screen, buttons, font, focus=None):
    # Draws all buttons. The button number focus lights up and gets amber corner marks.
    for i, button in enumerate(buttons):
        button.draw(screen, font, i == focus)
        if i == focus:
            theme.draw_brackets(screen, button.rect.inflate(10, 12).move(0, 1), FOCUS_COLOR, length=7)


def make_button_column(texts, center_x, top, width=240, height=50, gap=14):
    # Makes buttons stacked on top of each other.
    buttons = []
    for i, text in enumerate(texts):
        y = top + i * (height + gap)
        buttons.append(Button((center_x - width // 2, y, width, height), text))
    return buttons


def run_button_menu(screen, clock, buttons, draw_behind, escape_choice):
    # Shared loop for menus that are just a list of buttons (title screen and pause menu).
    # Returns the text of the button that was picked, escape_choice if Esc was pressed,
    # or None if the window was closed.
    # draw_behind(screen) draws everything except the buttons.
    font = pygame.font.SysFont(None, 34)
    focus = 0
    last_hovered = hovered_index(buttons)  # no sound for a button that is already under the mouse
    if last_hovered is not None:
        focus = last_hovered
    while True:
        # A new button under the mouse becomes the picked one.
        hovered = hovered_index(buttons)
        if hovered is not None and hovered != last_hovered:
            focus = hovered
            audio.play_sound("menu_hover")
        last_hovered = hovered

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return escape_choice
                elif event.key in (pygame.K_UP, pygame.K_w):
                    focus = (focus - 1) % len(buttons)
                    audio.play_sound("menu_hover")
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    focus = (focus + 1) % len(buttons)
                    audio.play_sound("menu_hover")
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    audio.play_sound("menu_select")
                    return buttons[focus].text
            for button in buttons:
                if button.is_clicked(event):
                    audio.play_sound("menu_select")
                    return button.text

        screen = pygame.display.get_surface()
        draw_behind(screen)
        draw_buttons(screen, buttons, font, focus)
        pygame.display.flip()
        clock.tick(FPS)


def open_options(clock, options):
    # Shows the options screen. Fullscreen may give us a new screen, so get it again.
    changed = options_module.options_screen(pygame.display.get_surface(), clock, options)
    if changed is not None and changed is not options:
        options.update(changed)  # keep using the same dict as clash.py
    return pygame.display.get_surface()


# --- Title screen ---

def title_screen(screen, clock, background):
    # Returns the text of the picked button, or None if the window was closed.
    title = make_title(theme.font("head", 150), "CLASH")
    center_x = SCREEN_WIDTH // 2
    buttons = make_button_column(["Play", "How to play", "Options", "Credits", "Quit"],
                                 center_x, 296, width=250, height=42, gap=11)
    panel = make_panel(310, 324, "Command")
    panel_rect = panel.get_rect(midtop=(center_x, 250))
    hints = theme.make_hint_line([("UP / DOWN", "choose"), ("ENTER", "select"), ("ESC", "quit")])

    def draw_behind(screen):
        draw_background(screen, background)
        # Small status text in the corners, like on a command screen.
        theme.blit_text(screen, "body", 13, "CLASH COMMAND  //  SECTOR 07", theme.KHAKI,
                        spacing=2, topleft=(20, 16))
        theme.blit_text(screen, "mono", 13, "GRID 90 x 70   HEX", HINT_COLOR, topleft=(20, 34))
        status = theme.blit_text(screen, "body", 13, "SYSTEM ONLINE", theme.KHAKI, spacing=2,
                                 topright=(SCREEN_WIDTH - 20, 16))
        light = theme.AMBER if theme.blink(1.6) else theme.AMBER_DIM
        pygame.draw.circle(screen, theme.EDGE_DARK, (status.left - 12, status.centery), 6)
        pygame.draw.circle(screen, light, (status.left - 12, status.centery), 4)
        draw_title(screen, title, (center_x, 128))
        theme.blit_text(screen, "body", 18, "CONQUER  THE  HEX  WORLD", theme.KHAKI, spacing=5,
                        shadow=True, center=(center_x, 222))
        screen.blit(panel, panel_rect)
        screen.blit(hints, hints.get_rect(center=(center_x, SCREEN_HEIGHT - 28)))
        theme.blit_text(screen, "mono", 13, f"BUILD {VERSION}", HINT_COLOR,
                        bottomright=(SCREEN_WIDTH - 20, SCREEN_HEIGHT - 20))

    return run_button_menu(screen, clock, buttons, draw_behind, "Quit")


# --- New game screen ---

def make_map_preview(map_type, seed, width, height):
    # Makes the same map the game will make, and shrinks it into a small picture.
    # A thin grid goes on top, like a map on a war table.
    tiles = maps.make_map(map_type, seed)
    preview = maps.make_preview(tiles, width, height)
    preview.blit(theme.make_grid_overlay(width, height, cell=23, alpha=0.5, extras=False), (0, 0))
    return preview


def draw_robot_dots(screen, count, center_x, y):
    # A small colored flag for every robot nation, so you can see how many there are.
    gap = 34
    left = center_x - (count - 1) * gap / 2
    for i in range(count):
        box = pygame.Rect(0, 0, 22, 14)
        box.center = (int(left + i * gap), y)
        pygame.draw.rect(screen, theme.EDGE_DARK, box.inflate(4, 4))
        pygame.draw.rect(screen, NATION_COLORS[i + 1], box)
        pygame.draw.line(screen, theme.EDGE, (box.left - 2, box.top - 2), (box.left - 2, box.bottom + 6), 2)


def setup_screen(screen, clock, background):
    # Lets the player pick robots, map type and seed.
    # Returns a setup dict, "back", or None if the window was closed.
    panel_rect = pygame.Rect(24, 18, SCREEN_WIDTH - 48, SCREEN_HEIGHT - 36)
    panel = make_panel(panel_rect.width, panel_rect.height, "Operation setup")
    preview_rect = pygame.Rect(56, 134, 460, 310)
    right_left = 560  # where the right column starts
    right_x = 720     # middle of the right column

    slider = Slider((right_x - 140, 178, 280, 8), MIN_ROBOTS, MAX_ROBOTS, START_ROBOTS,
                    whole_numbers=True)
    left_arrow = Button((right_x - 160, 276, 44, 44), "<")
    right_arrow = Button((right_x + 116, 276, 44, 44), ">")
    difficulty_left = Button((right_x - 160, 382, 44, 44), "<")
    difficulty_right = Button((right_x + 116, 382, 44, 44), ">")
    seed_button = Button((preview_rect.right - 150, preview_rect.bottom + 12, 150, 34), "New seed")
    back_button = Button((preview_rect.left, 510, 200, 50), "Back")
    start_button = Button((right_x - 130, 510, 260, 50), "Start", style="primary")
    buttons = [left_arrow, right_arrow, difficulty_left, difficulty_right,
               seed_button, back_button, start_button]
    hints = theme.make_hint_line([("LEFT/RIGHT", "robots"), ("UP/DOWN", "map"), ("TAB", "difficulty"),
                                  ("R", "seed"), ("ENTER", "start"), ("ESC", "back")], size=12)

    def make_setup():
        return {"robots": slider.value, "map_type": maps.MAP_TYPES[type_number], "seed": seed,
                "difficulty": DIFFICULTIES[difficulty]}

    type_number = 0
    difficulty = START_DIFFICULTY
    seed = seed_maker.randint(0, 999999)
    preview = make_map_preview(maps.MAP_TYPES[type_number], seed, preview_rect.width, preview_rect.height)
    last_hovered = None

    while True:
        hovered = hovered_index(buttons)
        if hovered is not None and hovered != last_hovered:
            audio.play_sound("menu_hover")
        last_hovered = hovered

        map_changed = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if slider.handle_event(event):
                audio.play_sound("menu_hover")
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "back"
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    audio.play_sound("menu_select")
                    return make_setup()
                elif event.key == pygame.K_TAB:
                    difficulty = (difficulty + 1) % len(DIFFICULTIES)
                    audio.play_sound("menu_select")
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    slider.value = max(MIN_ROBOTS, slider.value - 1)
                    audio.play_sound("menu_hover")
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    slider.value = min(MAX_ROBOTS, slider.value + 1)
                    audio.play_sound("menu_hover")
                elif event.key in (pygame.K_UP, pygame.K_w):
                    type_number = (type_number - 1) % len(maps.MAP_TYPES)
                    map_changed = True
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    type_number = (type_number + 1) % len(maps.MAP_TYPES)
                    map_changed = True
                elif event.key == pygame.K_r:
                    seed = seed_maker.randint(0, 999999)
                    map_changed = True
            if left_arrow.is_clicked(event):
                type_number = (type_number - 1) % len(maps.MAP_TYPES)
                map_changed = True
            elif right_arrow.is_clicked(event):
                type_number = (type_number + 1) % len(maps.MAP_TYPES)
                map_changed = True
            elif difficulty_left.is_clicked(event):
                difficulty = (difficulty - 1) % len(DIFFICULTIES)
                audio.play_sound("menu_select")
            elif difficulty_right.is_clicked(event):
                difficulty = (difficulty + 1) % len(DIFFICULTIES)
                audio.play_sound("menu_select")
            elif seed_button.is_clicked(event):
                seed = seed_maker.randint(0, 999999)
                map_changed = True
            elif back_button.is_clicked(event):
                audio.play_sound("menu_select")
                return "back"
            elif start_button.is_clicked(event):
                audio.play_sound("menu_select")
                return make_setup()

        if map_changed:
            audio.play_sound("menu_select")
            preview = make_map_preview(maps.MAP_TYPES[type_number], seed,
                                       preview_rect.width, preview_rect.height)

        screen = pygame.display.get_surface()
        draw_background(screen, background)
        screen.blit(panel, panel_rect)
        draw_heading(screen, "New game", "Brief // 01", preview_rect.left, 62)

        # The map preview on the left, in a target frame.
        theme.blit_text(screen, "body", 12, "THEATER MAP", HINT_COLOR, spacing=3,
                        bottomleft=(preview_rect.left, preview_rect.top - 6))
        theme.blit_text(screen, "mono", 13, maps.MAP_TYPES[type_number].upper(), theme.AMBER,
                        bottomright=(preview_rect.right, preview_rect.top - 5))
        pygame.draw.rect(screen, theme.EDGE_DARK, preview_rect.inflate(6, 6))
        screen.blit(preview, preview_rect)
        pygame.draw.rect(screen, theme.EDGE, preview_rect.inflate(6, 6), 1)
        theme.draw_brackets(screen, preview_rect.inflate(16, 16), theme.AMBER, length=14)
        theme.blit_text(screen, "body", 12, "SEED", HINT_COLOR, spacing=3,
                        midleft=(preview_rect.left, seed_button.rect.centery))
        theme.blit_text(screen, "mono", 18, f"{seed:06d}", theme.TEXT,
                        midleft=(preview_rect.left + 46, seed_button.rect.centery))

        # A thin line between the two columns.
        pygame.draw.line(screen, (70, 76, 60), (right_left - 10, 110), (right_left - 10, 480))

        # Robots on the right.
        theme.draw_tag(screen, "Forces", right_left, 128)
        theme.blit_text(screen, "body", 18, "Robot nations", theme.TEXT, midleft=(right_left + 76, 128))
        theme.blit_text(screen, "mono", 26, f"{slider.value}", theme.AMBER, midright=(SCREEN_WIDTH - 52, 128))
        slider.draw(screen)
        draw_robot_dots(screen, slider.value, right_x, 214)

        # Map type picker.
        draw_divider_y = 240
        theme.draw_divider(screen, right_left, SCREEN_WIDTH - 52, draw_divider_y)
        theme.draw_tag(screen, "Theater", right_left, 258)
        theme.blit_text(screen, "body", 18, "Map type", theme.TEXT, midleft=(right_left + 84, 258))
        theme.blit_text(screen, "mono", 14, f"{type_number + 1} / {len(maps.MAP_TYPES)}", HINT_COLOR,
                        midright=(SCREEN_WIDTH - 52, 258))
        theme.blit_text(screen, "head", 26, maps.MAP_TYPES[type_number].upper(), theme.AMBER, spacing=1,
                        center=(right_x, 298))

        # Difficulty picker.
        theme.draw_divider(screen, right_left, SCREEN_WIDTH - 52, 346)
        theme.draw_tag(screen, "Threat", right_left, 364)
        theme.blit_text(screen, "body", 18, "Robot difficulty", theme.TEXT, midleft=(right_left + 76, 364))
        theme.blit_text(screen, "head", 26, DIFFICULTIES[difficulty].upper(), DIFFICULTY_COLORS[difficulty],
                        spacing=1, center=(right_x, 404))
        theme.blit_text(screen, "body", 14, DIFFICULTY_NOTES[difficulty], HINT_COLOR, center=(right_x, 444))
        theme.draw_divider(screen, right_left, SCREEN_WIDTH - 52, 470)

        draw_buttons(screen, buttons, None)
        screen.blit(hints, hints.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 44)))
        pygame.display.flip()
        clock.tick(FPS)


# --- How to play and Credits ---

def run_info_screen(screen, clock, background, title, draw_page):
    # Shared loop for pages with only text and a Back button.
    # draw_page(screen) draws the text. Returns "back", or None if the window was closed.
    panel_rect = pygame.Rect(24, 18, SCREEN_WIDTH - 48, SCREEN_HEIGHT - 36)
    panel = make_panel(panel_rect.width, panel_rect.height, "Field manual")
    back_button = Button((SCREEN_WIDTH // 2 - 110, SCREEN_HEIGHT - 116, 220, 50), "Back")
    back_keys = (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
    hints = theme.make_hint_line([("ESC", "back"), ("ENTER", "back")])
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            elif event.type == pygame.KEYDOWN and event.key in back_keys:
                audio.play_sound("menu_select")
                return "back"
            elif back_button.is_clicked(event):
                audio.play_sound("menu_select")
                return "back"

        screen = pygame.display.get_surface()
        draw_background(screen, background)
        screen.blit(panel, panel_rect)
        draw_heading(screen, title, "Document // " + title, 56, 62)
        draw_page(screen)
        draw_buttons(screen, [back_button], None, 0)
        screen.blit(hints, hints.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 44)))
        pygame.display.flip()
        clock.tick(FPS)


def how_to_play_screen(screen, clock, background):
    # The rules on the left, all the keys on the right.
    rules_x = 56
    keys_x = SCREEN_WIDTH // 2 + 4
    key_width = max(theme.font("mono", 14).size(key.upper())[0] for key, action in options_module.CONTROLS)

    def draw_page(screen):
        theme.draw_tag(screen, "Rules of engagement", rules_x, 136)
        y = 156
        for line in RULES:
            if line:
                pygame.draw.rect(screen, theme.AMBER_DIM, (rules_x, y + 7, 5, 5))
                theme.blit_text(screen, "body", 16, line, theme.TEXT, topleft=(rules_x + 14, y))
                y += 23
            else:
                y += 9  # a small gap between the groups of rules
        pygame.draw.line(screen, (70, 76, 60), (keys_x - 22, 128), (keys_x - 22, 486))
        theme.draw_tag(screen, "Controls", keys_x, 136)
        y = 156
        for key, action in options_module.CONTROLS:
            theme.blit_text(screen, "mono", 14, key.upper(), theme.AMBER, topleft=(keys_x, y + 2))
            theme.blit_text(screen, "body", 15, action, theme.TEXT, topleft=(keys_x + key_width + 14, y + 1))
            y += 23

    return run_info_screen(screen, clock, background, "How to play", draw_page)


def credits_screen(screen, clock, background):
    def draw_page(screen):
        y = 168
        for i, line in enumerate(CREDITS):
            box = pygame.Rect(SCREEN_WIDTH // 2 - 280, y - 24, 560, 54)
            pygame.draw.rect(screen, (24, 28, 25), box)
            pygame.draw.rect(screen, (70, 76, 60), box, 1)
            pygame.draw.rect(screen, theme.AMBER, (box.left, box.top, 4, box.height))
            theme.blit_text(screen, "mono", 14, f"{i + 1:02d}", theme.AMBER, midleft=(box.left + 18, box.centery))
            theme.blit_text(screen, "body", 12, CREDIT_LABELS[i].upper(), HINT_COLOR, spacing=3,
                            midleft=(box.left + 52, box.centery))
            theme.blit_text(screen, "body", 20, line, theme.TEXT, midleft=(box.left + 170, box.centery))
            y += 70
        theme.blit_text(screen, "mono", 13, f"CLASH {VERSION}  //  END OF FILE", HINT_COLOR,
                        center=(SCREEN_WIDTH // 2, y - 6))

    return run_info_screen(screen, clock, background, "Credits", draw_page)


# --- The menus clash.py uses ---

def main_menu(screen, clock, options):
    # Shows the menus. Returns a game setup dict, or None if the player wants to quit.
    # A setup looks like {"robots": 3, "map_type": "Continents", "seed": 123456, "difficulty": "Normal"}.
    background = make_background()
    while True:
        choice = title_screen(screen, clock, background)
        if choice is None or choice == "Quit":
            return None
        elif choice == "Options":
            screen = open_options(clock, options)
        elif choice == "How to play":
            if how_to_play_screen(screen, clock, background) is None:
                return None
        elif choice == "Credits":
            if credits_screen(screen, clock, background) is None:
                return None
        elif choice == "Play":
            setup = setup_screen(screen, clock, background)
            if setup is None:
                return None
            if setup != "back":
                return setup
        screen = pygame.display.get_surface()


def pause_menu(screen, clock, options):
    # Shown when you press Esc in a game.
    # Returns "resume", "menu" (back to the main menu) or "quit".
    game_picture = darken(screen.copy(), 150)
    game_picture.blit(theme.make_grid_overlay(SCREEN_WIDTH, SCREEN_HEIGHT, alpha=0.7), (0, 0))
    panel = make_panel(330, 400, "Operation on hold")
    panel_rect = panel.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    buttons = make_button_column(["Resume", "Options", "Main menu", "Quit"],
                                 SCREEN_WIDTH // 2, panel_rect.top + 112, width=250, height=46, gap=12)
    stripes = theme.hazard_stripes(panel_rect.width - 60, 6)

    def draw_behind(screen):
        screen.blit(game_picture, (0, 0))
        screen.blit(panel, panel_rect)
        theme.blit_text(screen, "head", 52, "PAUSED", theme.AMBER, spacing=6, shadow=True,
                        center=(SCREEN_WIDTH // 2, panel_rect.top + 66))
        screen.blit(stripes, (panel_rect.left + 30, panel_rect.bottom - 40))
        theme.blit_text(screen, "body", 13, "ESC TO RESUME", HINT_COLOR, spacing=3,
                        center=(SCREEN_WIDTH // 2, panel_rect.bottom - 18))

    while True:
        choice = run_button_menu(screen, clock, buttons, draw_behind, "Resume")
        if choice is None or choice == "Quit":
            return "quit"
        elif choice == "Resume":
            return "resume"
        elif choice == "Main menu":
            return "menu"
        elif choice == "Options":
            screen = open_options(clock, options)
