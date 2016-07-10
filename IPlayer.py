# -*- coding: utf-8 -*-
import logging
import sys
import os
import signal
import subprocess

PLAYER_OMX = "omxplayer"
PLAYER_MPLAYER = "mplayer"

# definition of possible commands
CTRL_PLAY = "play"
CTRL_STOP = "stop"
CTRL_VOLUP = "volup"
CTRL_VOLDOWN = "voldown"

# definition of omxplayer commands
OMX_PLAY = "p"
OMX_VOLUP = "+"
OMX_VOLDOWN = "-"

# definition of mplayer commands
MPLAYER_PLAY = "p"
MPLAYER_VOLUP = "0"
MPLAYER_VOLDOWN = "9"

class IPlayer:
    def __init__(self):
        # dummy
        self.exist = True

    def __init__(self, player):
        self.p = 0
        self.log = logging.getLogger("IPlayer")
        streamH = logging.StreamHandler(sys.stderr)
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(streamH)
        self.log.debug("log inited")

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
        if self.p:
            self.stop()
        fullCMD = self.cmd + " " + stream
        # call the radio app and get the stdin
        self.p = subprocess.Popen(fullCMD, shell=True, stdin=subprocess.PIPE, preexec_fn=os.setsid)
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