# -*- coding: utf-8 -*-
import logging
import sys
import os
import signal
import subprocess
import parse
import time
from threading  import Thread
try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x

ON_POSIX = 'posix' in sys.builtin_module_names

PLAYER_OMX = "omxplayer"
PLAYER_MPLAYER = "mplayer -slave -quiet"    # the MPlayer is launched as slave support several commands

# definition of possible commands
CTRL_PLAY = "play"
CTRL_STOP = "stop"
CTRL_VOLUP = "volup"
CTRL_VOLDOWN = "voldown"

#Mplayer properties operations
GET = "get_property"
SET = "set_property"
STEP = "step_property"

#MPlayer possible requests (get / set / step)
OSDLEVEL = "osdlevel"
SPEED = "speed"
LOOP = "loop"
PAUSE = "pause"
FILENAME = "filename"
PATH = "path"
DEMUXER = "demuxer"
STREAM_POS = "stream_pos"
STREAM_START = "stream_start"
STREAM_END = "stream_end"
STREAM_LENGTH = "stream_length"
STREAM_TIME_P = "stream_time_p"
TITLES = "titles"
CHAPTER = "chapter"
CHAPTERS = "chapters"
ANGLE = "angle"
LENGTH = "length"
PERCENT_POS = "percent_pos"
TIME_POS = "time_pos"
METADATA = "metadata"
METADATA2 = "metadata/*"
VOLUME = "volume"
BALANCE = "balance"
MUTE = "mute"
AUDIO_DELAY = "audio_delay"
AUDIO_FORMAT = "audio_format"
AUDIO_CODEC = "audio_codec"
AUDIO_BITRATE = "audio_bitrate"
SAMPLERATE = "samplerate"
CHANNELS = "channels"
SWITCH_AUDIO = "switch_audio"
SWITCH_ANGLE = "switch_angle"
SWITCH_TITLE = "switch_title"
CAPTURING = "capturing"
FULLSCREEN = "fullscreen"
DEINTERLACE = "deinterlace"
ONTOP = "ontop"
ROOTWIN = "rootwin"
BORDER = "border"
FRAMEDROPPING = "framedropping"
GAMMA = "gamma"
BRIGHTNESS = "brightness"
CONTRAST = "contrast"
SATURATION = "saturation"
HUE = "hue"
PANSCAN = "panscan"
VSYNC = "vsync"
VIDEO_FORMAT = "video_format"
VIDEO_CODEC = "video_codec"
VIDEO_BITRATE = "video_bitrate"
WIDTH = "width"
HEIGHT = "height"
FPS = "fps"
ASPECT = "aspect"
SWITCH_VIDEO = "switch_video"
SWITCH_PROGRA = "switch_progra"
SUB = "sub"
SUB_SOURCE = "sub_source"
SUB_FILE = "sub_file"
SUB_VOB = "sub_vob"
SUB_DEMUX = "sub_demux"
SUB_DELAY = "sub_delay"
SUB_POS = "sub_pos"
SUB_ALIGNMENT = "sub_alignment"
SUB_VISIBILIT = "sub_visibilit"
SUB_FORCED_ON = "sub_forced_on"
SUB_SCALE = "sub_scale"
TV_BRIGHTNESS = "tv_brightness"
TV_CONTRAST = "tv_contrast"
TV_SATURATION = "tv_saturation"
TV_HUE = "tv_hue"
TELETEXT_PAGE = "teletext_page"
TELETEXT_SUBP = "teletext_subp"
TELETEXT_MODE = "teletext_mode"
TELETEXT_FORM = "teletext_form"
TELETEXT_HALF = "teletext_half"

# definition of omxplayer commands
OMX_PLAY = "p"
OMX_VOLUP = "+"
OMX_VOLDOWN = "-"

# definition of mplayer commands
MPLAYER_PLAY = "pause\n"
MPLAYER_VOLUP = "step_property volume 1\n"
MPLAYER_VOLDOWN = "step_property volume -1\n"

def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()

class IPlayer:
    PRE_ARG = ""
    def __init__(self):
        # dummy
        self.exist = True

    def __init__(self, player, prearg=False):
        self.p = 0
        self.log = logging.getLogger("IPlayer")
        streamH = logging.StreamHandler(sys.stderr)
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(streamH)
        self.log.debug("log inited")

        if prearg is not False:
            self.log.debug("Setting prearg " + prearg)
            IPlayer.PRE_ARG = prearg        # this is global, because even when new instance is created we should use it
        self.cmd = player
        # by default always use MPlayer map
        self.ctrl_play = MPLAYER_PLAY
        self.ctrl_volup = MPLAYER_VOLUP
        self.ctrl_voldown = MPLAYER_VOLDOWN
        if player == PLAYER_MPLAYER:
            self.ctrl_play = MPLAYER_PLAY
            self.ctrl_volup = MPLAYER_VOLUP
            self.ctrl_voldown = MPLAYER_VOLDOWN
        elif player == PLAYER_OMX:
            self.ctrl_play = OMX_PLAY
            self.ctrl_volup = OMX_VOLUP
            self.ctrl_voldown = OMX_VOLDOWN

    def play(self, stream):
        """
        :param stream: The stream to open (URL or Path)
        :type stream: str

        :return nothing
        :rtype: None
        """
        if self.p and self.cmd == PLAYER_OMX:
            self.stop()
        if IPlayer.PRE_ARG != "":
            fullCMD = IPlayer.PRE_ARG + " " + self.cmd + " " + stream
        else:
            fullCMD = self.cmd + " " + stream
        # call the radio app and get the stdin
        self.p = subprocess.Popen(fullCMD, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, preexec_fn=os.setsid, bufsize=1, close_fds=ON_POSIX)
        self.q = Queue()
        self.read_thread = Thread(target=enqueue_output, args=(self.p.stdout, self.q))
        self.read_thread.daemon = True # thread dies with the program
        self.read_thread.start()
        self.log.info("Radio App started!")

    def stop(self):
        try:
            if self.p:
                os.killpg(os.getpgid(self.p.pid), signal.SIGTERM)
        except Exception as err:
            self.log.debug("Failed stopping player")
            pass

    def send_control(self, ctrl):
        if ctrl == CTRL_PLAY:
            ctrl = self.ctrl_play
        elif ctrl == CTRL_VOLDOWN:
            ctrl = self.ctrl_voldown
        elif ctrl == CTRL_VOLUP:
            ctrl = self.ctrl_volup
        elif ctrl == CTRL_STOP:
            self.stop()
            return
        else:
            self.log.error("Unsupported control " + ctrl)
            return
        self.p.stdin.write( ctrl )
        self.p.stdin.flush()
        self.log.info("Command {0} sent to radio".format(ctrl))

    def get_value(self, val):
        """
        :param val: The property to get
        :param val: str
        :return: the answer
        :rtype: str
        """
        self.p.stdin.write(GET + " " + val + "\n")
        self.p.stdin.flush()
        self.log.info("Command {0} sent to radio".format(GET + " " + val))
        n_tries = 10
        while n_tries > 0:
            try:  # Try to parse
                line = self.read_stdout()
                ret = parse.search("={}\n", line)
                if ret is not None and len(ret.fixed) != 0:
                    self.log.debug("got " + ret.fixed[0] + " to get of " + val)
                    return ret.fixed[0]
            except Exception as err:
                self.log.debug("Attempts {0}".format(n_tries))
                time.sleep(0.1)
                n_tries -= 1
                continue

    def read_stdout(self):
        return self.q.get_nowait()
