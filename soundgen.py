import math
import os
import random
import wave
from array import array

# Makes all music and sound effects with math, and saves them as .wav files.
# Everything is the same every time (no real randomness), so the files can
# always be deleted and made again.

RATE = 22050  # samples per second
VERSION = 1  # change this when the sounds change, so old cached files are not used


def note_freq(note):
    # Turns a note number into a frequency. 69 is A (440 Hz), 60 is middle C.
    # One step up is one piano key up, 12 steps up is one octave up.
    return 440 * 2 ** ((note - 69) / 12)


def empty(seconds):
    # A silent piece of sound, as a list of numbers between -1 and 1.
    return [0.0] * int(seconds * RATE)


def add_tone(samples, start, length, freq, volume, shape="triangle", attack=0.01,
             release=0.05, decay=0.0, slide=0.0, duty=0.5, wrap=True):
    # Adds one note to samples.
    #   start, length: in seconds
    #   shape: "triangle", "square", "sine" or "noise"
    #   attack, release: seconds to fade in and fade out (no clicks)
    #   decay: bigger number = the note dies away faster (like a plucked string)
    #   slide: how many Hz the pitch moves per second (for "pew" and "boom" sounds)
    #   duty: for squares, how much of the wave is "up" (0.5 is a normal square, smaller is thinner)
    #   wrap: if the note goes past the end, continue at the start (for music that loops)
    total = len(samples)
    first = int(start * RATE)
    count = int(length * RATE)
    noise = random.Random(1)
    noise_value = 0.0
    phase = 0.0
    for i in range(count):
        t = i / RATE

        # Where in the wave we are (0 to 1), moved forward by the frequency.
        phase += (freq + slide * t) / RATE
        if phase >= 1:
            phase -= int(phase)
            noise_value = noise.uniform(-1, 1)

        if shape == "triangle":
            value = 4 * abs(phase - 0.5) - 1
        elif shape == "square":
            value = 1 if phase < duty else -1
        elif shape == "sine":
            value = math.sin(2 * math.pi * phase)
        else:
            value = noise_value

        # How loud the note is right now (the "envelope").
        level = volume
        if t < attack:
            level *= t / attack
        if decay > 0:
            level *= math.exp(-decay * t)
        if t > length - release:
            level *= (length - t) / release

        index = first + i
        if index >= total:
            if not wrap:
                break
            index = index % total
        samples[index] += value * level


def add_echo(samples, delay, amount):
    # Mixes in a quieter copy of the sound a bit later, like an echo in a big room.
    # Negative indexes wrap around to the end, which is what a loop needs.
    step = int(delay * RATE)
    for i in range(len(samples)):
        samples[i] += samples[i - step] * amount


def soften(samples, amount):
    # A simple low-pass filter: removes the sharp, buzzy part of square waves.
    # amount near 0 is very soft and muffled, 1 changes nothing.
    smooth = samples[-1]
    for i in range(len(samples)):
        smooth += (samples[i] - smooth) * amount
        samples[i] = smooth


def mix_into(samples, other):
    for i in range(len(samples)):
        samples[i] += other[i]


def save_wav(samples, path, loudness):
    # Scales the sound so the loudest point is at loudness (0 to 1), then writes a .wav file.
    peak = max(max(samples), -min(samples), 0.0001)
    scale = loudness * 32767 / peak
    data = array("h", [int(value * scale) for value in samples])
    # Write to a temporary file first, so a half-written file is never used.
    temp_path = path + ".tmp"
    with wave.open(temp_path, "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(RATE)
        file.writeframes(data.tobytes())
    os.replace(temp_path, path)


# ---------- Drums ----------

def add_kick(samples, start, volume):
    # A low "boom": a sine wave that quickly drops in pitch.
    add_tone(samples, start, 0.22, 130, volume, "sine", attack=0.002, release=0.05,
             decay=14, slide=-380)


def add_snare(samples, start, volume):
    add_tone(samples, start, 0.16, 7000, volume, "noise", attack=0.002, release=0.04, decay=22)
    add_tone(samples, start, 0.10, 190, volume * 0.8, "triangle", attack=0.002, release=0.03,
             decay=30)


def add_hat(samples, start, volume):
    add_tone(samples, start, 0.05, 11000, volume, "noise", attack=0.001, release=0.02, decay=60)


# ---------- Music ----------

def make_menu_music(path):
    # Calm and floaty: A minor, 80 beats per minute, 8 bars of 4 beats (24 seconds).
    beat = 60 / 80
    bar = beat * 4
    # Each bar has a chord (three notes) and a bass note.
    chords = [[57, 60, 64], [57, 60, 65], [55, 60, 64], [55, 59, 62],
              [57, 60, 64], [57, 60, 65], [57, 62, 65], [56, 59, 64]]
    bass = [45, 41, 48, 43, 45, 41, 38, 40]
    # The tune: (beat in the bar, length in beats, note) for every bar.
    melody = [
        [(0, 2, 76), (2, 1, 74), (3, 1, 72)],
        [(0, 3, 72), (3, 1, 69)],
        [(0, 2, 67), (2, 2, 72)],
        [(0, 3, 71), (3, 1, 74)],
        [(0, 2, 76), (2, 1, 79), (3, 1, 76)],
        [(0, 3, 77), (3, 1, 76)],
        [(0, 2, 74), (2, 2, 72)],
        [(0, 2, 71), (2, 2, 68)],
    ]
    arp_order = [0, 1, 2, 1, 0, 1, 2, 1]  # which chord note each eighth note plays

    music = empty(bar * 8)
    lead = empty(bar * 8)  # tune and arpeggio get an echo, the rest does not
    for b in range(8):
        bar_start = b * bar
        # Soft pad: the chord held for the whole bar.
        for note in chords[b]:
            add_tone(music, bar_start, bar, note_freq(note), 0.07, "triangle",
                     attack=0.5, release=0.9)
        # Bass on beat 1 and beat 3.
        for half in range(2):
            add_tone(music, bar_start + half * 2 * beat, beat * 2, note_freq(bass[b]), 0.32,
                     "triangle", attack=0.02, release=0.3, decay=1.2)
        # Gentle arpeggio, one octave up.
        for step in range(8):
            note = chords[b][arp_order[step]] + 12
            add_tone(lead, bar_start + step * beat / 2, beat / 2, note_freq(note), 0.07,
                     "triangle", attack=0.01, release=0.08, decay=5)
        # The tune: a thin square wave, quiet.
        for start_beat, length_beats, note in melody[b]:
            add_tone(lead, bar_start + start_beat * beat, length_beats * beat, note_freq(note),
                     0.06, "square", attack=0.04, release=0.25, decay=0.8, duty=0.25)
        # A very quiet shaker between the beats.
        for step in range(4):
            add_hat(music, bar_start + step * beat + beat / 2, 0.025)

    add_echo(lead, beat * 0.75, 0.35)
    mix_into(music, lead)
    soften(music, 0.4)
    save_wav(music, path, 0.8)


def make_game_music(path):
    # Steady and a bit tense: D minor, 112 beats per minute, 16 bars (about 34 seconds).
    beat = 60 / 112
    bar = beat * 4
    # Every chord lasts two bars.
    chords = [[57, 62, 65], [58, 62, 65], [55, 60, 64], [57, 60, 64],
              [57, 62, 65], [58, 62, 65], [55, 58, 62], [57, 61, 64]]
    bass = [38, 34, 36, 33, 38, 34, 31, 33]
    # Tune rhythm over two bars: (beat, length in beats, which chord note).
    tune_rhythm = [(0, 1.5, 2), (1.5, 0.5, 1), (2, 2, 0), (4, 1, 1), (5, 1, 2), (6, 2, 1)]

    music = empty(bar * 16)
    lead = empty(bar * 16)
    for c in range(8):
        chord_start = c * bar * 2
        chord = chords[c]
        for step in range(16):
            # Bass: eighth notes that jump between low and high.
            note = bass[c] + (12 if step % 2 == 1 else 0)
            add_tone(music, chord_start + step * beat / 2, beat / 2 * 0.9, note_freq(note),
                     0.3, "triangle", attack=0.005, release=0.04, decay=5)
        for b in range(2):
            bar_start = chord_start + b * bar
            # Short chord stabs just after beats 2 and 4.
            for stab_beat in [1.5, 3.5]:
                for note in chord:
                    add_tone(music, bar_start + stab_beat * beat, beat * 0.4, note_freq(note),
                             0.035, "square", attack=0.005, release=0.06, decay=6, duty=0.25)
            # Drums: kick on 1 and 3, snare on 2 and 4, hats on every eighth note.
            add_kick(music, bar_start, 0.5)
            add_kick(music, bar_start + 2 * beat, 0.5)
            add_snare(music, bar_start + beat, 0.09)
            add_snare(music, bar_start + 3 * beat, 0.09)
            for step in range(8):
                add_hat(music, bar_start + step * beat / 2, 0.03 if step % 2 == 0 else 0.018)
        if c < 4:
            # First half: one soft high note per chord, with a long echo.
            add_tone(lead, chord_start, beat * 3, note_freq(chord[2] + 12), 0.06, "triangle",
                     attack=0.05, release=0.5, decay=0.8)
        else:
            # Second half: a short tune made from the chord notes.
            for start_beat, length_beats, index in tune_rhythm:
                add_tone(lead, chord_start + start_beat * beat, length_beats * beat,
                         note_freq(chord[index] + 12), 0.05, "square", attack=0.02,
                         release=0.15, decay=1.5, duty=0.25)

    add_echo(lead, beat * 0.75, 0.4)
    mix_into(music, lead)
    soften(music, 0.5)
    save_wav(music, path, 0.8)


# ---------- Sound effects ----------

def make_click(path):
    sound = empty(0.08)
    add_tone(sound, 0, 0.07, 1046, 1, "triangle", attack=0.002, release=0.03, decay=40,
             wrap=False)
    save_wav(sound, path, 0.5)


def make_menu_hover(path):
    sound = empty(0.05)
    add_tone(sound, 0, 0.045, 1568, 1, "triangle", attack=0.002, release=0.02, decay=50,
             wrap=False)
    save_wav(sound, path, 0.25)


def make_menu_select(path):
    sound = empty(0.2)
    add_tone(sound, 0, 0.08, 784, 1, "square", attack=0.002, release=0.02, decay=20, duty=0.25,
             wrap=False)
    add_tone(sound, 0.07, 0.12, 1175, 1, "square", attack=0.002, release=0.05, decay=18,
             duty=0.25, wrap=False)
    soften(sound, 0.5)
    save_wav(sound, path, 0.45)


def make_start(path):
    # A rising "let's go" arpeggio: C E G C.
    sound = empty(0.75)
    notes = [60, 64, 67, 72]
    for i, note in enumerate(notes):
        length = 0.4 if i == len(notes) - 1 else 0.1
        add_tone(sound, i * 0.09, length, note_freq(note + 12), 1, "square", attack=0.003,
                 release=0.08, decay=5, duty=0.25, wrap=False)
        add_tone(sound, i * 0.09, length, note_freq(note), 0.6, "triangle", attack=0.003,
                 release=0.08, decay=5, wrap=False)
    soften(sound, 0.45)
    save_wav(sound, path, 0.6)


def make_capture(path):
    # A short "pop" that slides up.
    sound = empty(0.1)
    add_tone(sound, 0, 0.09, 520, 1, "triangle", attack=0.002, release=0.03, decay=25,
             slide=5000, wrap=False)
    save_wav(sound, path, 0.4)


def make_attack(path):
    # A soft thud with a bit of noise, like marching boots or a far-away cannon.
    sound = empty(0.25)
    add_tone(sound, 0, 0.22, 220, 1, "triangle", attack=0.002, release=0.06, decay=16,
             slide=-500, wrap=False)
    add_tone(sound, 0, 0.12, 3000, 0.5, "noise", attack=0.002, release=0.04, decay=30,
             wrap=False)
    soften(sound, 0.35)
    save_wav(sound, path, 0.55)


def make_victory(path):
    # A happy little fanfare that ends on a big major chord.
    sound = empty(1.8)
    notes = [(0.0, 67), (0.12, 72), (0.24, 76), (0.36, 79)]
    for start, note in notes:
        add_tone(sound, start, 0.14, note_freq(note), 0.8, "square", attack=0.003,
                 release=0.04, decay=4, duty=0.25, wrap=False)
    for note in [60, 64, 67, 72, 76]:
        add_tone(sound, 0.5, 1.3, note_freq(note), 0.4, "triangle", attack=0.01, release=0.6,
                 decay=1.5, wrap=False)
    add_tone(sound, 0.5, 1.3, note_freq(84), 0.25, "square", attack=0.01, release=0.6,
             decay=2, duty=0.25, wrap=False)
    soften(sound, 0.45)
    save_wav(sound, path, 0.7)


def make_defeat(path):
    # A slow, sad line going down, ending on a low minor chord.
    sound = empty(2.0)
    notes = [(0.0, 69), (0.3, 67), (0.6, 65), (0.9, 64)]
    for start, note in notes:
        add_tone(sound, start, 0.32, note_freq(note), 0.7, "square", attack=0.01,
                 release=0.1, decay=2, duty=0.25, wrap=False)
    for note in [45, 57, 60, 64]:
        add_tone(sound, 1.2, 0.8, note_freq(note), 0.4, "triangle", attack=0.02, release=0.5,
                 decay=1.5, wrap=False)
    soften(sound, 0.35)
    save_wav(sound, path, 0.65)


# Which function makes which sound.
MUSIC_MAKERS = {
    "menu": make_menu_music,
    "game": make_game_music,
}

SOUND_MAKERS = {
    "click": make_click,
    "menu_hover": make_menu_hover,
    "menu_select": make_menu_select,
    "start": make_start,
    "capture": make_capture,
    "attack": make_attack,
    "victory": make_victory,
    "defeat": make_defeat,
}
