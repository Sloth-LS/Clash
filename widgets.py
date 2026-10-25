import pygame

from settings import *
import theme

# Buttons look like metal switch plates with a small light on the left.
# The light turns amber when the button is under the mouse or picked with the keyboard.
BUTTON_COLOR = theme.PLATE_LIGHT
BUTTON_HOVER_COLOR = theme.PLATE_HOVER
BUTTON_EDGE_COLOR = theme.EDGE
PRIMARY_COLOR = (196, 128, 32)        # the amber plate of the most important button
PRIMARY_HOVER_COLOR = theme.AMBER
PRIMARY_TEXT_COLOR = (24, 20, 12)

# Finished button pictures, so each one is only drawn once.
button_pictures = {}


def make_button_picture(width, height, text, lit, style):
    # Draws one button (not lit or lit) into its own picture.
    picture = pygame.Surface((width, height + 3), pygame.SRCALPHA)
    rect = pygame.Rect(0, 0, width, height)
    cut = min(10, height // 4)
    primary = style == "primary"
    if primary:
        fill = PRIMARY_HOVER_COLOR if lit else PRIMARY_COLOR
        edge = (255, 214, 140) if lit else (120, 78, 20)
    else:
        fill = BUTTON_HOVER_COLOR if lit else BUTTON_COLOR
        edge = theme.AMBER if lit else BUTTON_EDGE_COLOR

    # A dark copy a bit lower makes the plate look raised.
    pygame.draw.polygon(picture, theme.EDGE_DARK, theme.chamfer_points(rect.move(0, 3), cut))
    pygame.draw.polygon(picture, fill, theme.chamfer_points(rect, cut))
    # Light top edge and dark bottom edge, like a bevel.
    top_color = tuple(min(255, c + 28) for c in fill)
    pygame.draw.line(picture, top_color, (cut + 1, 1), (width - cut // 3 - 2, 1))
    pygame.draw.polygon(picture, edge, theme.chamfer_points(rect, cut), 2 if lit else 1)

    if text in ("<", ">"):
        # Arrow buttons get a drawn triangle instead of a letter.
        color = PRIMARY_TEXT_COLOR if primary else (theme.AMBER if lit else theme.KHAKI)
        mid_x, mid_y = width // 2, height // 2
        size = height // 5
        if text == "<":
            points = [(mid_x - size, mid_y), (mid_x + size // 2 + 2, mid_y - size), (mid_x + size // 2 + 2, mid_y + size)]
        else:
            points = [(mid_x + size, mid_y), (mid_x - size // 2 - 2, mid_y - size), (mid_x - size // 2 - 2, mid_y + size)]
        pygame.draw.polygon(picture, color, points)
        return picture

    # The small indicator light on the left.
    if text in ("On", "Off"):
        light_on = text == "On"
        light = theme.GREEN if light_on else (110, 44, 34)
        pygame.draw.circle(picture, theme.EDGE_DARK, (18, height // 2), 7)
        pygame.draw.circle(picture, light, (18, height // 2), 5)
        if light_on:
            pygame.draw.circle(picture, (220, 255, 190), (16, height // 2 - 2), 1)
    elif not primary:
        light = theme.AMBER if lit else theme.AMBER_DIM
        pygame.draw.rect(picture, theme.EDGE_DARK, (8, 9, 6, height - 18))
        pygame.draw.rect(picture, light, (9, 10, 4, height - 20))

    # The text: big buttons get bigger letters.
    size = 20 if height >= 44 else 17
    if primary:
        color = PRIMARY_TEXT_COLOR
    else:
        color = (255, 244, 220) if lit else theme.TEXT
    label = theme.text("body", size, text.upper(), color, spacing=2)
    middle = (width // 2 + (6 if text in ("On", "Off") else 0), height // 2)
    picture.blit(label, label.get_rect(center=middle))
    return picture


class Button:
    # A box with text that you can click.
    # style "primary" gives an amber plate for the most important button on a screen.
    def __init__(self, rect, text, style="normal"):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.style = style

    def is_hovered(self):
        return self.rect.collidepoint(pygame.mouse.get_pos())

    def is_clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.rect.collidepoint(event.pos))

    def draw(self, screen, font, lit=False):
        # font is not used any more (the theme picks the font), but other modules still pass it.
        lit = lit or self.is_hovered()
        key = (self.rect.width, self.rect.height, self.text, lit, self.style)
        if key not in button_pictures:
            button_pictures[key] = make_button_picture(self.rect.width, self.rect.height,
                                                       self.text, lit, self.style)
        screen.blit(button_pictures[key], self.rect.topleft)


class Slider:
    # A track with a knob you can drag. value goes from low to high.
    def __init__(self, rect, low, high, value, whole_numbers=False):
        self.rect = pygame.Rect(rect)
        self.low = low
        self.high = high
        self.value = value
        self.whole_numbers = whole_numbers
        self.dragging = False

    def set_from_mouse(self, mouse_x):
        fraction = (mouse_x - self.rect.left) / self.rect.width
        fraction = max(0, min(1, fraction))
        value = self.low + fraction * (self.high - self.low)
        if self.whole_numbers:
            value = round(value)
        self.value = value

    def handle_event(self, event):
        # Returns True if the value changed.
        old_value = self.value
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.inflate(30, 40).collidepoint(event.pos):
                self.dragging = True
                self.set_from_mouse(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.set_from_mouse(event.pos[0])
        return self.value != old_value

    def draw(self, screen):
        # A sunken groove with ruler marks, an amber fill and a lever-like handle.
        groove = pygame.Rect(self.rect.left, self.rect.centery - 4, self.rect.width, 8)
        fraction = (self.value - self.low) / (self.high - self.low)
        knob_x = int(self.rect.left + fraction * self.rect.width)

        # Ruler marks under the groove: one for every whole number, or every 10 %.
        steps = self.high - self.low if self.whole_numbers and self.high - self.low <= 20 else 10
        for i in range(steps + 1):
            x = self.rect.left + round(i * self.rect.width / steps)
            height = 7 if i in (0, steps) or (steps == 10 and i == 5) else 4
            pygame.draw.line(screen, theme.EDGE, (x, groove.bottom + 5), (x, groove.bottom + 5 + height))

        pygame.draw.rect(screen, SLIDER_TRACK_COLOR, groove)
        fill = groove.copy()
        fill.width = knob_x - groove.left
        if fill.width > 0:
            pygame.draw.rect(screen, theme.AMBER_DIM, fill)
            pygame.draw.line(screen, SLIDER_KNOB_COLOR, (fill.left, fill.centery), (fill.right - 1, fill.centery), 2)
        pygame.draw.rect(screen, theme.EDGE, groove, 1)

        # The handle.
        handle = pygame.Rect(0, 0, 14, 28)
        handle.center = (knob_x, groove.centery)
        pygame.draw.rect(screen, theme.EDGE_DARK, handle.move(0, 2))
        pygame.draw.polygon(screen, theme.KHAKI if not self.dragging else SLIDER_KNOB_COLOR,
                            theme.chamfer_points(handle, 4, 0))
        pygame.draw.polygon(screen, theme.EDGE_DARK, theme.chamfer_points(handle, 4, 0), 1)
        for dy in (-5, 0, 5):
            pygame.draw.line(screen, (90, 86, 64), (handle.left + 4, handle.centery + dy),
                             (handle.right - 5, handle.centery + dy))
