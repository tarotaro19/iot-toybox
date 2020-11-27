import json
import threading
from playsound import playsound
#import mplayer
import vlc
import simpleaudio
import subprocess
import time
from mplayer import Player, CmdPrefix

## installtion
# $sudo apt install libasound2-dev

'''
wav_obj = simpleaudio.WaveObject.from_wave_file("sounds/bgm_maoudamashii_8bit29.wav")
play_obj = wav_obj.play()
print('play start')
play_obj.wait_done()
'''

'''
player = vlc.MediaPlayer()
player.set_mrl('sounds/bgm_maoudamashii_8bit29.mp3')
player.play()
print('play start')
'''

'''
p=subprocess.Popen(['mplayer', 'sounds/bgm_maoudamashii_8bit29.mp3'], shell=False)
print('play with subprocess')
time.sleep(5)
'''

# Set default prefix for all Player instances
Player.cmd_prefix = CmdPrefix.PAUSING_KEEP
# Since autospawn is True by default, no need to call player.spawn() manually
player = Player()
# Play a file
player.loadfile('sounds/bgm_maoudamashii_8bit29.mp3')
player.loop = 0
while True:
    time.sleep(1)

player2 = Player()
player2.loadfile('sounds/se_maoudamashii_magical08.mp3')
time.sleep(5)

