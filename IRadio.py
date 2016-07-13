# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import subprocess
import youtube_dl
import logging
import os
import sys
import parse
import requests
import ConfigParser
import threading
import time
import IPlayer
import IDisplay

SEPARATOR = chr(29)     # GS
defRadioCMD = IPlayer.PLAYER_OMX

#definition of possible sources
SRC_YOUTUBE = "youtube"
SRC_RADIO = "radio"
SRC_MEDIA = "media"     # generic - will attempt to parse and get the stream

#define the Media Parsing Keys
MEDIA_KEY_YOUTUBE = "youtu"
MEDIA_KEY_HTTP = "http"
MEDIA_KEY_PLAYLIST= "pls"

#definition of possible system commands
CMD_POWER = "pwr"


class IRadio:
    NOW_PLAYING = "...nothing playing..."

    def __init__(self):
        print ""

    def __init__(self, nodisp=False, prearg=""):
        """
        :param nodisp: Enables/Disables usage of OLED display
        :type nodisp: bool
        :param prearg: Argument to pass before player command
        :type prearg: str
        """
        self.player = IPlayer.IPlayer(defRadioCMD, prearg)
        if nodisp:
            self.display = IDisplay.IDisplay_fake()
        else:
            self.display = IDisplay.IDisplay()
        self.log = logging.getLogger("IRadio")
        streamH = logging.StreamHandler(sys.stderr)
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(streamH)
        self.log.debug("IRadio log inited")

        self.update_playing_thread = update_now_playing(1, "update_playing_thread", self.log, self.display)
        self.update_playing_thread.setDaemon(1)
        self.update_playing_thread.start()

    def play(self, path):
        self.player.play(path)

    def stop(self):
        self.player.stop()

    def youtube_track(self, link):
        """
        :param link: the youtube content Link
        :type link: str
        :return: none
        """
        # youtube allways has to play with OMX
        self.player.stop()      # before creating new stop a potentially playing player
        self.player = IPlayer.IPlayer(IPlayer.PLAYER_OMX)
        url, title = get_video_url(link)
        self.player.play(url)
        self.log.debug("playing " + title)
        IRadio.NOW_PLAYING = title

    def local_track(self, path):
        """
        :param path: the path to the local resource
        :type path: str
        :return: none
        """
        self.player.stop()      # before creating new stop a potentially playing player
        self.player = IPlayer.IPlayer(IPlayer.PLAYER_MPLAYER)
        path = os.path.normpath(path)
        path = path.replace(" ", "\ ")
        self.player.play(path)
        self.log.debug("playing " + path.substring(path.lastIndexOf("/")+1, path.length()))
        IRadio.NOW_PLAYING = path.substring(path.lastIndexOf("/")+1, path.length())

    def local_playlist(self, pls_path):
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
            self.player.play(stream)
        else:
            self.log.error("No valid playlist in " + pls_path)
            return

    def online_playlist(self, link):
        """

        :param link: the link of the playlist
        :type link: str
        :return: nothing
        """
        self.player.stop()      # before creating new stop a potentially playing player
        self.player = IPlayer.IPlayer(IPlayer.PLAYER_MPLAYER)
        self.player.play("-playlist " + link)
        self.log.debug("playing " + link)
        IRadio.NOW_PLAYING = link;


    def mediaParse(self, media):
        """
        :param media: the media content string
        :type media: str

        :return: none
        """
        # check if it's youtube
        if media.__contains__(MEDIA_KEY_YOUTUBE):
            self.log.debug("Link seems to be youtube...")
            self.youtube_track(media)
        # check if media is local content by checking if file exists
        elif os.path.isfile(media):
            self.log.debug("Seems to be local content...")
            self.local_track(media)
        # check is the media is local folder
        elif os.path.isdir(media):
            self.log.debug("Seems to be local folder...")
            if media.endswith("/"):
                media = media + "*"
            else:
                media = media + "/*"
            self.local_track(media)
        # check if is online playlist
        elif media.startswith(MEDIA_KEY_HTTP) and media.endswith(MEDIA_KEY_PLAYLIST):
            self.log.debug("Seems online playlist...")
            self.online_playlist(media)

        # attempt playing whatever it is with MPlayer
        else:
            self.player.stop()  # before creating new stop a potentially playing player
            self.player = IPlayer.IPlayer(IPlayer.PLAYER_MPLAYER)
            self.player.play(media)
            IRadio.NOW_PLAYING = media
            self.log.debug("playing " + media)


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
                if SRC_MEDIA.lower() == ret.fixed[0].lower():
                    cmd = cmd.replace("src="+ret.fixed[0], "")
                    self.log.debug("Trying to find media in " + cmd)
                    ret = parse.search(SEPARATOR + "{}" + SEPARATOR, cmd)
                    if ret is not None and len(ret.fixed) != 0:
                        self.log.debug("Trying to parse " + ret.fixed[0])
                        self.mediaParse(ret.fixed[0])
                        return
                return

            ret = parse.search("ctrl={:w}" + SEPARATOR, cmd)
            if ret is not None and len(ret.fixed) != 0:
                self.player.send_control(ret.fixed[0].lower())
                return

            ret = parse.search("cmd={:w}" + SEPARATOR, cmd)
            if ret is not None and len(ret.fixed) != 0:
                # Is Power Off?
                if CMD_POWER.lower() == ret.fixed[0].lower():
                    self.p = subprocess.Popen("sudo init 0", shell=True, stdin=subprocess.PIPE, preexec_fn=os.setsid)
                    return
                # TODO process commands
                # TODO think of a way of saving/managing the added radio stations (local/remote?)
                return

        except Exception as err:
            self.log.error("ERR: Couldn't process message" + err.message)
            pass


    def get_now_playing(self):
        """
        :return: the Playing content
        :rtype: str
        """
        # TODO implement
        # MPlayer allows to get via API
        if self.player.cmd == IPlayer.PLAYER_MPLAYER:
            while 1:
                try:
                    line = self.player.read_stdout()
                    if line.startswith('ICY Info:'):
                        self.log.debug("\t\t" + line)
                        IRadio.NOW_PLAYING = ""
                        ret = parse.search("StreamTitle='{}';", line)
                        if ret is not None and len(ret.fixed) != 0:
                            self.log.debug("sending " + ret.fixed[0])
                            IRadio.NOW_PLAYING = ret.fixed[0]
                        return IRadio.NOW_PLAYING
                except Exception as err:
                    return IRadio.NOW_PLAYING
        else:
            return IRadio.NOW_PLAYING


class update_now_playing(threading.Thread):
    def __init__(self, threadID, name, logger, disp):
        """

        :param threadID: Thread's ID
        :type threadID: int
        :param name: Thread's name
        :type name: str
        :param logger: the logger
        :type logger: Logger
        :param disp: the display
        :type disp: IDisplay.IDisplay

        :return: nothing
        """
        threading.Thread.__init__(self)

        self.log = logger
        self.disp = disp

        self.b_continue = True
        self.now_playing = ""

    def run(self):
        # now keep updating
        while self.b_continue:
            try:
                if self.now_playing != IRadio.NOW_PLAYING:
                    self.now_playing = IRadio.NOW_PLAYING
                    self.disp.set_now_playing(self.now_playing)
                time.sleep(0.5)               # Sleep 500ms
            except Exception as err:
                self.log.error("Exception getting now playing: " + err.message)
                pass


    def __stop(self):
        try:
            self.b_continue = False
        except Exception as err:
            log.error("Excetion stopping thread " + err.message)
            pass


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

    :return: the parsed URL for the video, title
    :rtype: {str,str}
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

    return ("\"" + video.get('url') + "\"", video.get('title'))