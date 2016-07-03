# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import youtube_dl
import logging
import os
import signal
import sys
import subprocess
import parse
import requests
import ConfigParser

SEPARATOR = chr(29)     # GS
defRadioCMD = "omxplayer"

#definition of possible sources
SRC_YOUTUBE = "youtube"
SRC_RADIO = "radio"

#definition of possible commands
CMD_PLAY = "play"
CMD_VOLUP = "volup"
CMD_VOLDOWN = "voldown"

#definition of omxplayer commands
OMX_PLAY = "p"
OMX_VOLUP = "+"
OMX_VOLDOWN = "-"

class MyLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)


def my_hook(d):
    """

    :param d: Dict with messages
    :return: nothing
    """
    if d['status'] == 'finished':
        print('Done downloading, now converting ...')


def get_video_url(link):
    """

    :param link: The link to parse URL
    :type link: unicode

    :return: the parsed URL for the video
    :rtype: str
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'logger': MyLogger(),
        'progress_hooks': [my_hook],
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(link, download=False)
        except Exception:
            return u''

    if 'entries' in result:
        # Can be a playlist or a list of videos
        video = result['entries'][0]
    else:
        # Just a video
        video = result

    return "\"" + video.get('url') + "\""


class IRadio:
    def __init__(self):
        self.log.debug("dummy init")

    def __init__(self, player_cmd=defRadioCMD):
        """

        :param player_cmd:  The alternative radio command
         :type player_cmd: str
        """
        self.radioCMD = player_cmd
        self.initialize_commons()

    def initialize_commons(self):
        self.log = logging.getLogger("IRadio")
        streamH = logging.StreamHandler(sys.stderr)
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(streamH)
        self.log.debug("log inited")
        self.p = 0

    def play(self, stream):
        """
        :param stream: The stream to open (URL or Path)
        :type stream: str

        :return nothing
        :rtype: None
        """
        if self.p:
            self.stop()
        fullCMD = self.radioCMD + " " + stream
        #call the radio app and get the stdin
        self.p = subprocess.Popen(fullCMD, shell=True, stdin=subprocess.PIPE, preexec_fn=os.setsid)
        self.log.info("Radio App started!")

    def stop(self):
        if self.p:
            os.killpg(os.getpgid(self.p.pid), signal.SIGTERM)

    def sendCmd(self, cmd):
        self.p.stdin.write( cmd )
        self.p.stdin.flush()
        self.log.info("Command {0} sent to radio".format(cmd))

    def radio_playlist(self, pls_path):
        """

        :param pls_path: The playlist file path
        :type pls_path: str
        :return: nothing
        """
        pls = ConfigParser.ConfigParser()
        pls.read(pls_path)
        if "playlist" in pls.sections():
            self.log.debug("found valid playlist in " + pls_path)
            n_entries = pls.get("playlist", "NumberOfEntries")
            if n_entries is None:
                self.log.error("Playlist found, but no entries found on the playlist")
                return
            stream = pls.get("playlist", "File1")
            if stream is None:
                self.log.error("Playlist found, but no stream found on the playlist")
                return
            self.play(stream)
        else:
            self.log.error("No valid playlist in " + pls_path)
            return

    def process_command(self, cmd):
        """
        :param cmd: Frame
        :type cmd: str

        :return nothing
        :rtype: None
        """
        try:
            ret = parse.search("src={:w}"+SEPARATOR, cmd)
            if ret is not None and len(ret.fixed) != 0:
                if SRC_YOUTUBE.lower() == ret.fixed[0].lower():
                    ret = parse.search("link={}" + SEPARATOR, cmd)
                    self.play(get_video_url(ret.fixed[0]))
                elif SRC_RADIO.lower() == ret.fixed[0].lower():
                    ret = parse.search("url={}" + SEPARATOR, cmd)
                    if ret is not None and len(ret.fixed) != 0:
                        self.play(ret.fixed[0])
                        return
                    ret = parse.search("link={}" + SEPARATOR, cmd)
                    if ret is not None and len(ret.fixed) != 0:
                        resp = requests.get(ret.fixed[0])
                        if resp.status_code == 200:
                            with open("playlist.pls", "wb") as playlist_file:
                                playlist_file.write(resp.content)
                            self.radio_playlist( os.path.abspath(playlist_file.name))
                        return
                    ret = parse.search("pls={}" + SEPARATOR, cmd)
                    if ret is not None and len(ret.fixed) != 0:
                        self.radio_playlist(ret.fixed[0])
                        return
                return

            ret = parse.search("cmd={:w}" + SEPARATOR, cmd)
            if ret is not None and len(ret.fixed) != 0:
                if CMD_PLAY.lower() == ret.fixed[0].lower():
                    self.sendCmd(OMX_PLAY)


        except Exception as err:
            self.log.error("ERR: Couldn't process message" + err.message)
            pass
