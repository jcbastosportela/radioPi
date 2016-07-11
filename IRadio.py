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

#definition of possible system commands
CMD_POWER = "pwr"


class IRadio:
    NOW_PLAYING = "NAV"

    def __init__(self):
        print ""

    def __init__(self, player_cmd=defRadioCMD):
        """
        :param player_cmd:  The alternative radio command
         :type player_cmd: str
        """
        self.display = IDisplay.IDisplay()
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

    def stop(self):
        self.player.stop()

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
        #self.display.setNowPlaying(title)
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
        #self.display.setNowPlaying(path.substring(path.lastIndexOf("/")+1, path.length()))
        self.log.debug("playing " + path.substring(path.lastIndexOf("/")+1, path.length()))
        IRadio.NOW_PLAYING = path.substring(path.lastIndexOf("/")+1, path.length())

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
        # attempt playing whatever it is with MPlayer
        else:
            self.player.stop()  # before creating new stop a potentially playing player
            self.player = IPlayer.IPlayer(IPlayer.PLAYER_MPLAYER)
            self.player.play(media)
            #self.display.setNowPlaying(media)
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

                if SRC_YOUTUBE.lower() == ret.fixed[0].lower():
                    ret = parse.search("link={}" + SEPARATOR, cmd)
                    if ret is not None:
                        self.youtube_track(ret.fixed[0])
                    return

                if SRC_RADIO.lower() == ret.fixed[0].lower():
                    # radio allways has to play with MPlayer
                    self.player = IPlayer.IPlayer(IPlayer.PLAYER_MPLAYER)
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


def get_now_playing():
    """
    :return: the Playing content
    :rtype: str
    """
    # TODO implement
    return IRadio.NOW_PLAYING
    # MPlayer allows to get via API
    #if self.player.cmd == IPlayer.PLAYER_MPLAYER:


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