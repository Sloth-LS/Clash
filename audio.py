import os
import sys

import pygame

import soundgen

# Music and sound effects. Every function is safe to call even if there is no sound card.
# The sounds are made by soundgen.py the first time they are needed and saved in the
# "sounds" folder, so the next start is fast. Deleting the folder is always fine.



def sound_folder():
    # As a PyInstaller .exe, __file__ points into a temporary folder that is deleted
    # when the game closes, so the sounds are kept next to the .exe instead.
    if getattr(sys, "frozen", False):
        folder = os.path.dirname(sys.executable)
    else:
        folder = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(folder, "sounds")


working = False  # becomes True when the sound system started without problems
sounds = {}  # sound effect name -> pygame Sound
current_music = None  # name of the music track that is playing now
music_volume = 0.5
sound_volume = 0.7


def file_path(name):
    # The version number is in the name, so changed sounds get new files.
    return os.path.join(sound_folder(), f"{name}_v{soundgen.VERSION}.wav")


def make_file(name, maker):
    # Makes the .wav file if it is not in the folder yet. Returns its path.
    path = file_path(name)
    if not os.path.exists(path):
        maker(path)
    return path


def init(options):
    # Starts the sound system. Call once, after pygame.init().
    global working
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        os.makedirs(sound_folder(), exist_ok=True)
        # The folder only holds files we can make again, so tell git to skip it.
        ignore_file = os.path.join(sound_folder(), ".gitignore")
        if not os.path.exists(ignore_file):
            with open(ignore_file, "w") as file:
                file.write("*\n")
        # Sound effects are short, so make and load all of them now.
        # Music is made later, the first time it is played.
        for name, maker in soundgen.SOUND_MAKERS.items():
            sounds[name] = pygame.mixer.Sound(make_file(name, maker))
        working = True
    except Exception:
        # No sound card, no disk space, ... The game just stays quiet.
        working = False
    apply_volumes(options)


def apply_volumes(options):
    # Uses "music_volume" and "sound_volume" from the options.
    global music_volume, sound_volume
    music_volume = options.get("music_volume", 0.5)
    sound_volume = options.get("sound_volume", 0.7)
    if not working:
        return
    try:
        pygame.mixer.music.set_volume(music_volume)
        for sound in sounds.values():
            sound.set_volume(sound_volume)
    except Exception:
        pass


def play_music(name):
    # Starts a music track that loops, e.g. "menu" or "game". Does nothing if it is already playing.
    global current_music
    if not working or name == current_music or name not in soundgen.MUSIC_MAKERS:
        return
    try:
        path = make_file(name, soundgen.MUSIC_MAKERS[name])
        pygame.mixer.music.load(path)
        pygame.mixer.music.play(loops=-1, fade_ms=1000)
        pygame.mixer.music.set_volume(music_volume)
        current_music = name
    except Exception:
        current_music = None


def stop_music():
    global current_music
    current_music = None
    if not working:
        return
    try:
        pygame.mixer.music.fadeout(500)
    except Exception:
        pass


def play_sound(name):
    # Plays a short sound effect once, e.g. "click" or "start".
    if not working or name not in sounds:
        return
    try:
        sounds[name].play()
    except Exception:
        pass
