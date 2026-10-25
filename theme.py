import math

import pygame

from settings import *

# The "War Command" look: gunmetal and olive plates, amber lights,
# hard cut corners and small stencil labels, like a military command table.
# Everything here only draws things. Pictures that take time to make are made once
# and kept in a dict, so drawing them every frame stays fast.

# --- Colors (red, green, blue) ---
GUNMETAL = (20, 24, 25)        # the darkest background
PLATE = (33, 38, 33)           # the color of panels
PLATE_LIGHT = (50, 57, 46)     # buttons
PLATE_HOVER = (68, 76, 56)     # a button under the mouse
HEADER = (46, 52, 38)          # the strip at the top of a panel
EDGE = (104, 110, 82)          # thin olive edges
EDGE_DARK = (10, 12, 12)       # shadows and outlines
KHAKI = (205, 194, 150)        # labels and headings
TEXT = MENU_TEXT_COLOR         # normal text
DIM = HINT_COLOR               # small grey-green text
AMBER = (242, 164, 46)         # the signal color for everything important
AMBER_DIM = (104, 72, 30)      # an amber light that is off
RED = (214, 72, 52)
GREEN = (142, 186, 92)

# Windows fonts. If one is missing, pygame just picks a normal font instead.
FONT_NAMES = {
    "head": "impact",       # big stencil-like headings
    "body": "bahnschrift",  # labels, buttons and normal text
    "mono": "consolas",     # numbers
}

fonts = {}
texts = {}
pictures = {}


def font(kind, size):
    if (kind, size) not in fonts:
        fonts[(kind, size)] = pygame.font.SysFont(FONT_NAMES[kind], size)
    return fonts[(kind, size)]


def text(kind, size, words, color, spacing=0):
    # Renders text once and keeps it. spacing puts extra pixels between the letters,
    # which makes small labels look like they are stamped on metal.
    key = (kind, size, words, color, spacing)
    if key not in texts:
        if len(texts) > 600:
            texts.clear()  # numbers change, so don't keep old ones forever
        the_font = font(kind, size)
        if spacing == 0:
            texts[key] = the_font.render(words, True, color)
        else:
            letters = [the_font.render(letter, True, color) for letter in words]
            width = sum(letter.get_width() for letter in letters) + spacing * max(0, len(letters) - 1)
            surface = pygame.Surface((max(1, width), the_font.get_height()), pygame.SRCALPHA)
            x = 0
            for letter in letters:
                surface.blit(letter, (x, 0))
                x += letter.get_width() + spacing
            texts[key] = surface
    return texts[key]


def blit_text(screen, kind, size, words, color, spacing=0, shadow=False, **position):
    # Draws text placed with any pygame.Rect position, like midleft=(x, y). Returns its box.
    label = text(kind, size, words, color, spacing)
    rect = label.get_rect(**position)
    if shadow:
        screen.blit(text(kind, size, words, EDGE_DARK, spacing), rect.move(1, 2))
    screen.blit(label, rect)
    return rect


# --- Shapes ---

def chamfer_points(rect, cut, small=None):
    # The corners of a box with the top-left and bottom-right corners cut off
    # (the other two get a smaller cut). This is the main shape of the whole look.
    if small is None:
        small = cut // 3
    left, top, right, bottom = rect.left, rect.top, rect.right - 1, rect.bottom - 1
    return [(left + cut, top), (right - small, top), (right, top + small),
            (right, bottom - cut), (right - cut, bottom), (left + small, bottom),
            (left, bottom - small), (left, top + cut)]


def lighter(color, amount):
    # A lighter copy of a color (the 4th number, how see-through it is, stays the same).
    return tuple(min(255, c + amount) for c in color[:3]) + tuple(color[3:])


def draw_scanlines(surface, color, rect, gap=3):
    # Thin lines across a box, like an old screen. color must already be the line color,
    # because drawing on a see-through picture replaces the pixels instead of mixing them.
    for y in range(rect.top + 1, rect.bottom - 1, gap):
        pygame.draw.line(surface, color, (rect.left, y), (rect.right - 1, y))


def draw_rivet(surface, x, y):
    # A tiny screw head.
    pygame.draw.circle(surface, EDGE_DARK, (x, y + 1), 2)
    pygame.draw.circle(surface, (120, 124, 98), (x, y), 2)
    surface.set_at((x - 1, y - 1), (190, 190, 160))


def draw_ticks(surface, x, y, count, gap, color, tall_every=5):
    # A row of small ruler marks.
    for i in range(count):
        height = 5 if i % tall_every == 0 else 3
        pygame.draw.line(surface, color, (x + i * gap, y), (x + i * gap, y + height))


def hazard_stripes(width, height):
    # Amber and black warning stripes.
    key = ("hazard", width, height)
    if key not in pictures:
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        surface.fill((25, 20, 12))
        for x in range(-height, width + height, 10):
            pygame.draw.polygon(surface, AMBER, [(x, height), (x + 5, height), (x + 5 + height, 0), (x + height, 0)])
        pictures[key] = surface
    return pictures[key]


def make_plate(width, height, title=None, cut=14, alpha=232, fill=PLATE):
    # A metal panel: cut corners, a double edge, rivets, ruler marks and
    # (if a title is given) a darker strip at the top with a small stencil label.
    key = ("plate", width, height, title, cut, alpha, fill)
    if key in pictures:
        return pictures[key]
    rect = pygame.Rect(0, 0, width, height)
    plate = pygame.Surface((width, height), pygame.SRCALPHA)
    plate.fill(fill + (alpha,))

    # Faint lines across the plate, like a screen or brushed metal.
    draw_scanlines(plate, lighter(fill, 5) + (alpha,), rect)

    if title is not None:
        pygame.draw.rect(plate, HEADER + (245,), (0, 0, width, 28))
        pygame.draw.line(plate, EDGE, (0, 28), (width, 28))
        pygame.draw.rect(plate, AMBER, (cut + 6, 9, 6, 11))
        label = text("body", 15, title.upper(), KHAKI, spacing=3)
        plate.blit(label, label.get_rect(midleft=(cut + 20, 15)))
        draw_ticks(plate, width - 70, 10, 9, 6, EDGE)

    # Cut the corners off: everything outside the shape becomes see-through.
    mask = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), chamfer_points(rect, cut))
    plate.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

    # The double edge.
    pygame.draw.polygon(plate, EDGE, chamfer_points(rect, cut), 2)
    inner = rect.inflate(-10, -10)
    pygame.draw.polygon(plate, (62, 68, 54), chamfer_points(inner, max(2, cut - 4)), 1)

    # Rivets near the corners that are not cut much.
    draw_rivet(plate, width - 10, 10 if title is None else 40)
    draw_rivet(plate, 10, height - 10)
    # Ruler marks at the bottom.
    draw_ticks(plate, cut + 14, height - 9, 12, 5, (78, 84, 64))

    pictures[key] = plate
    return plate


def draw_brackets(screen, rect, color, length=12, width=2):
    # Four corner marks around a box, like a target frame.
    left, top, right, bottom = rect.left, rect.top, rect.right - 1, rect.bottom - 1
    for x, y, dx, dy in ((left, top, 1, 1), (right, top, -1, 1), (left, bottom, 1, -1), (right, bottom, -1, -1)):
        pygame.draw.line(screen, color, (x, y), (x + dx * length, y), width)
        pygame.draw.line(screen, color, (x, y), (x, y + dy * length), width)


def draw_tag(screen, words, x, y, color=AMBER):
    # A small amber label box like "FORCES", with its middle-left at (x, y). Returns its box.
    label = text("body", 12, words.upper(), (20, 18, 12), spacing=2)
    box = pygame.Rect(x, y - 9, label.get_width() + 12, 18)
    pygame.draw.polygon(screen, color, chamfer_points(box, 5, 0))
    screen.blit(label, label.get_rect(center=box.center))
    return box


def draw_divider(screen, left, right, y):
    # A thin line with a small notch at the start.
    pygame.draw.line(screen, (84, 90, 70), (left, y), (right, y))
    pygame.draw.line(screen, AMBER, (left, y), (left + 18, y), 2)


def keycap(words, size=13):
    # A small key like [ESC], for the hints.
    key = ("keycap", words, size)
    if key not in pictures:
        label = text("mono", size, words, AMBER)
        width = max(label.get_width() + 12, size + 8)
        height = size + 9
        cap = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(cap, (14, 16, 16), (0, 1, width, height - 1))
        pygame.draw.rect(cap, (54, 60, 50), (0, 0, width, height - 2))
        pygame.draw.rect(cap, EDGE, (0, 0, width, height - 2), 1)
        cap.blit(label, label.get_rect(center=(width // 2, (height - 2) // 2)))
        pictures[key] = cap
    return pictures[key]


def make_hint_line(parts, size=13):
    # parts is a list of (key, what it does), drawn as keycaps with text. Made once.
    key = ("hints", tuple(parts), size)
    if key not in pictures:
        pieces = []
        for cap_text, action in parts:
            pieces.append((keycap(cap_text, size), text("body", size + 1, action, DIM)))
        width = 0
        for cap, label in pieces:
            width += cap.get_width() + 6 + label.get_width() + 18
        height = size + 9
        line = pygame.Surface((max(1, width - 18), height), pygame.SRCALPHA)
        x = 0
        for cap, label in pieces:
            line.blit(cap, (x, 0))
            x += cap.get_width() + 6
            line.blit(label, label.get_rect(midleft=(x, height // 2 - 1)))
            x += label.get_width() + 18
        pictures[key] = line
    return pictures[key]


# --- Backgrounds ---

def make_grid_overlay(width, height, cell=32, alpha=1.0, extras=True):
    # A see-through map grid with range rings, scan lines and dark corners.
    # extras False gives only the grid and scan lines (for small map pictures).
    key = ("grid", width, height, cell, alpha, extras)
    if key in pictures:
        return pictures[key]
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    # Scan lines.
    for y in range(0, height, 3):
        pygame.draw.line(overlay, (0, 0, 0, int(40 * alpha)), (0, y), (width, y))
    # The grid, with a stronger line every 4 cells.
    for i, x in enumerate(range(0, width, cell)):
        strength = 40 if i % 4 == 0 else 18
        pygame.draw.line(overlay, (210, 200, 150, int(strength * alpha)), (x, 0), (x, height))
    for i, y in enumerate(range(0, height, cell)):
        strength = 40 if i % 4 == 0 else 18
        pygame.draw.line(overlay, (210, 200, 150, int(strength * alpha)), (0, y), (width, y))
    if not extras:
        pictures[key] = overlay
        return overlay
    # Range rings around the middle, like a radar.
    center = (width // 2, height // 2)
    for radius in range(120, max(width, height), 120):
        pygame.draw.circle(overlay, (242, 164, 46, int(26 * alpha)), center, radius, 1)
    pygame.draw.line(overlay, (242, 164, 46, int(30 * alpha)), (center[0], 0), (center[0], height))
    pygame.draw.line(overlay, (242, 164, 46, int(30 * alpha)), (0, center[1]), (width, center[1]))
    # Dark corners: a few see-through frames that get darker towards the edge.
    for i in range(24):
        darkness = int((24 - i) * 5 * alpha)
        pygame.draw.rect(overlay, (0, 0, 0, darkness), (i * 4, i * 4, width - i * 8, height - i * 8), 4)
    pictures[key] = overlay
    return overlay


def draw_backdrop(screen):
    # A plain command-room background for screens without the map (the options screen).
    if "backdrop" not in pictures:
        backdrop = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        backdrop.fill(GUNMETAL)
        backdrop.blit(make_grid_overlay(SCREEN_WIDTH, SCREEN_HEIGHT), (0, 0))
        pictures["backdrop"] = backdrop
    screen.blit(pictures["backdrop"], (0, 0))
    draw_sweep(screen)


SWEEP_SPEED = 30     # degrees the radar line turns every second
SWEEP_SLICES = 18    # the glow behind the line is made of this many thin slices
SWEEP_SLICE = 2.0    # degrees per slice


def draw_sweep(screen):
    # A slow radar line that turns around the middle of the screen with a soft glow behind it.
    # The glow is drawn on a black layer and then added to the screen, so it only brightens.
    if "sweep" not in pictures:
        pictures["sweep"] = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    layer = pictures["sweep"]
    layer.fill((0, 0, 0))
    center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
    reach = SCREEN_WIDTH + SCREEN_HEIGHT
    angle = pygame.time.get_ticks() / 1000 * SWEEP_SPEED

    def point(degrees):
        radians = math.radians(degrees)
        return (center_x + reach * math.cos(radians), center_y + reach * math.sin(radians))

    for i in range(SWEEP_SLICES):
        brightness = 1 - i / SWEEP_SLICES
        color = (int(34 * brightness), int(24 * brightness), int(8 * brightness))
        start = angle - i * SWEEP_SLICE
        pygame.draw.polygon(layer, color, [(center_x, center_y), point(start), point(start - SWEEP_SLICE - 0.3)])
    pygame.draw.line(layer, (120, 84, 26), (center_x, center_y), point(angle), 2)
    screen.blit(layer, (0, 0), special_flags=pygame.BLEND_RGB_ADD)


def blink(period=1.0):
    # True for half of every period (in seconds). Used for small blinking lights.
    return (pygame.time.get_ticks() / 1000) % period < period / 2
