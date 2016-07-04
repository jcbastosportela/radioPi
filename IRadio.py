# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import youtube_dl
import logging
import os
import sys
import parse
import requests
import ConfigParser
import IPlayer

SEPARATOR = chr(29)     # GS
defRadioCMD = IPlayer.PLAYER_OMX

#definition of possible sources
SRC_YOUTUBE = "youtube"
SRC_RADIO = "radio"


class IRadio:
    def __init__(self, player_cmd=defRadioCMD):
        """

        :param player_cmd:  The alternative radio command
         :type player_cmd: str
        """
        self.player = IPlayer.IPlayer(player_cmd)
        self.initialize_commons()

    def initialize_commons(self):
        self.log = logging.getLogger("IRadio")
        streamH = logging.StreamHandler(sys.stderr)
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(streamH)
        self.log.debug("log inited")

    def play(self, path):
        self.player.play(path)

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
            self.player.play(stream)
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
                    self.player.play(get_video_url(ret.fixed[0]))
                elif SRC_RADIO.lower() == ret.fixed[0].lower():
                    ret = parse.search("url={}" + SEPARATOR, cmd)
                    if ret is not None and len(ret.fixed) != 0:
                        self.player.play(ret.fixed[0])
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

            ret = parse.search("ctrl={:w}" + SEPARATOR, cmd)
            if ret is not None and len(ret.fixed) != 0:
                self.player.send_control(ret.fixed[0].lower())
                return

            ret = parse.search("cmd={:w}" + SEPARATOR, cmd)
            if ret is not None and len(ret.fixed) != 0:
                # TODO process commands
                # TODO think of a way of saving/managing the added radio stations (local/remote?)
                return

        except Exception as err:
            self.log.error("ERR: Couldn't process message" + err.message)
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