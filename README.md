# Clash

Clash is a pixel strategy game where civilizations fight for land on a map made of hexagons.
You start with a small piece of land, grow your troops and attack your neighbors.
Whoever owns most of the map wins.

Made with Python and pygame-ce for Hack Club Terra.

## Features (so far)

- Random map of land and water, made with cellular automata
- Hexagon tiles, each with 6 neighbors
- Click a tile to select it (it shows if it is land or water)
- Press space to make a new map

## How to run

You need Python 3.13 and pygame-ce.

    py -3.13 -m pip install pygame-ce
    py -3.13 clash.py

## Controls

| Key / mouse | What it does    |
|-------------|-----------------|
| Left click  | Select a tile   |
| Space       | Make a new map  |
| Esc         | Quit            |

## Roadmap

- [x] Map with land and water
- [ ] Players and bots with their own colors and start tiles
- [ ] Troops that grow over time
- [ ] Attacks that move the border tile by tile
- [ ] Slider for how many troops to send, and a HUD
- [ ] Bots that attack on their own
- [ ] Start screen, game over and win screen
- [ ] Extras: cities, mountains, boats, alliances, nukes

## Inspiration

Inspired by OpenFront.io. All code and graphics in Clash are my own.
