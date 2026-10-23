# Clash

A very simplified, real-time territory game in the style of Civ and [OpenFront](https://openfront.io), built with Python and pygame.

You and a number of robot nations start on a random hex map. You earn soldiers over time, the more land you own the more soldiers you get, and you send them out to take empty land and to attack the other nations. The last nation standing wins.

## Status

Work in progress. This is what works so far:

- Random hex map with land and water
- Start screen with a slider to pick how many robot nations to play against (1 to 7)
- Every nation gets a capital, a color and a bit of starting land
- Nation names drawn on the map
- Camera: move around and zoom in and out

## How to run

You need Python 3 and pygame:

```
pip install pygame
python Clash.py
```

## Controls

| Key / mouse | What it does |
|---|---|
| Slider or ← → | Pick how many robot nations (start screen) |
| Enter | Start the game |
| W A S D or arrow keys | Move the camera |
| Mouse wheel | Zoom in and out toward the mouse |
| Left click | Select a tile |
| Space | Make a new map |
| Esc | Quit |

## Plan

- [x] Start screen with robot slider
- [x] Capitals, colors and starting land
- [x] Camera (move and zoom)
- [ ] Pick your own start spot, with 10 seconds to change your mind after the first pick
- [ ] Nation names centered in their land and sized to fit inside the border
- [ ] Soldiers that grow every second, faster the more land you own
- [ ] Double-click to send soldiers to take land or attack another nation
- [ ] Robot nations that expand and attack on their own
- [ ] Boats you can see sailing, to attack across water

## Known bugs

- **The game opens again after you close it.** When you try to close the window, the game starts up again instead of quitting. Not fixed yet.
