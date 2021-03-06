# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import subprocess
import youtube_dl
import logging
import os
import sys
import parse
import codecs
import ConfigParser
import threading
import time
import IPlayer
import IDisplay

SEPARATOR = chr(29)     # GS
FRAME_HEAD = chr(0x02)  #STX
FRAME_TAIL = chr(0x03)  #ETX
defRadioCMD = IPlayer.PLAYER_OMX

# the file with the playlists
PI_RADIO_LISTS = "./radiopi.lrp"
RPL_RADIO = "radio"
RPL_YOUTUBE = "youtube"
RPL_NENTRIES = "NumberOfEntries"
RPL_ENTRY = "entry{0}"
RPL_ENTRY_NAME = "name{0}"

#definition of possible sources
SRC_YOUTUBE = "youtube"
SRC_RADIO = "radio"
SRC_LOCAL = "local"
SRC_MEDIA = "media"     # generic - will attempt to parse and get the stream

#define the Media Parsing Keys
MEDIA_KEY_HTTPS = "https"
MEDIA_KEY_YOUTUBE = "youtu"
MEDIA_KEY_HTTP = "http"
MEDIA_KEY_PLS_PLAYLIST= ".pls"
MEDIA_KEY_ASX_PLAYLIST = ".asx"

#definition of possible system commands
CMD_POWER = "pwr"
CMD_GET_PLAYLIST = "gpls"


class IRadio:
    NOW_PLAYING = "...nothing playing..."
    RADIO_NAME = "..."
    RADIO_GENRE = "..."
    RADIO_BITRATE = "..."
    SRC = "NONE"

    def __init__(self):
        """

        """
        print ""

    def __init__(self, tcpsndr, nodisp=False, prearg=""):
        """
        :param tcpsndr: the TCP sender interface
        :type tcpsndr: TCPSender
        :param nodisp: Enables/Disables usage of OLED display
        :type nodisp: bool
        :param prearg: Argument to pass before player command
        :type prearg: str
        """
        self.tcpsend = tcpsndr
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

        # load the playlists
        self.rplist = ConfigParser.ConfigParser()
        if not os.path.isfile(PI_RADIO_LISTS):
            # if it doesn't exist lets create
            self.create_radiopi_list_file()
            self.rplistfile = codecs.open(PI_RADIO_LISTS, 'r+', encoding='utf-8')
            self.rplist.read(PI_RADIO_LISTS)
        else:
            self.rplistfile = codecs.open(PI_RADIO_LISTS, 'r+', encoding='utf-8')
            self.rplist.read(PI_RADIO_LISTS)
            try:
                self.rplist.get(RPL_RADIO, RPL_NENTRIES, 0)
                self.rplist.get(RPL_YOUTUBE, RPL_NENTRIES, 0)
            except ConfigParser.NoSectionError as err:
                self.log.info("Creating new RadioPiList: " + err.message)
                self.create_radiopi_list_file()
                self.rplistfile = codecs.open(PI_RADIO_LISTS, 'r+', encoding='utf-8')
                self.rplist.read(PI_RADIO_LISTS)

        self.update_playing_thread = update_now_playing(1, "update_playing_thread", self.log, self)
        self.update_playing_thread.setDaemon(1)
        self.update_playing_thread.start()

    def create_radiopi_list_file(self):
        """

        :return: nothing
        """
        try:
            self.rplistfile.close()
        except:
            pass
        self.rplist.add_section(RPL_RADIO)
        self.rplist.set(RPL_RADIO, RPL_NENTRIES, "0" )
        self.rplist.add_section(RPL_YOUTUBE)
        self.rplist.set(RPL_YOUTUBE, RPL_NENTRIES, "0" )

        self.rplistfile = open(PI_RADIO_LISTS, 'w')
        self.rplist.write(self.rplistfile)
        try:
            self.rplistfile.close()
        except:
            pass



    def play(self, path):
        """

        :param path: the path to play
        :type path: str
        :return: nothing
        """
        self.player.play(path)

    def stop(self):
        """

        :return: nothing
        """
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
        #self.log.debug("playing " + path.substring(path.lastIndexOf("/")+1, path.length()))
        IRadio.NOW_PLAYING = path

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
        IRadio.NOW_PLAYING = link


    def mediaParse(self, media):
        """
        :param media: the media content string
        :type media: str

        :return: the type of source parsed
        """
        # check if it's youtube
        if media.startswith(MEDIA_KEY_HTTP) and media.__contains__(MEDIA_KEY_YOUTUBE):
            self.log.debug("Link seems to be youtube...")
            self.youtube_track(media)
            IRadio.SRC = SRC_YOUTUBE
            return  SRC_YOUTUBE
        # check if media is local content by checking if file exists
        elif os.path.isfile(media):
            self.log.debug("Seems to be local content...")
            self.local_track(media)
            IRadio.SRC = SRC_LOCAL
            return  SRC_LOCAL
        # check is the media is local folder
        elif os.path.isdir(media):
            self.log.debug("Seems to be local folder...")
            if media.endswith("/"):
                media = media + "*"
            else:
                media = media + "/*"
            self.local_track(media)
            IRadio.SRC = SRC_LOCAL
            return  SRC_LOCAL
        # check if is online playlist
        elif media.startswith(MEDIA_KEY_HTTP) and ( media.__contains__(MEDIA_KEY_PLS_PLAYLIST) or
                                                    media.__contains__(MEDIA_KEY_ASX_PLAYLIST) ):
            self.log.debug("Seems online playlist...")
            self.online_playlist(media)
            IRadio.SRC = SRC_RADIO
            return  SRC_RADIO
        # infact anything else that is http lets say it's radio
        elif media.startswith(MEDIA_KEY_HTTP):
            self.player.stop()  # before creating new stop a potentially playing player
            self.player = IPlayer.IPlayer(IPlayer.PLAYER_MPLAYER)
            self.player.play(media)
            IRadio.NOW_PLAYING = media
            self.log.debug("playing " + media)
            IRadio.SRC = SRC_RADIO
            return  SRC_RADIO
        # attempt playing whatever it is with MPlayer
        else:
            self.player.stop()  # before creating new stop a potentially playing player
            self.player = IPlayer.IPlayer(IPlayer.PLAYER_MPLAYER)
            self.player.play(media)
            IRadio.NOW_PLAYING = media
            self.log.debug("playing " + media)
            IRadio.SRC = SRC_MEDIA
            return  SRC_MEDIA

    def rplist_add(self, src, val, name=""):
        """

        :param src: the source
        :type src: str
        :param val: the value (link)
        :type val: str
        :param name: the name
        :type name: str
        :return: nothing
        """
        n_entries = self.rplist.get(src, RPL_NENTRIES, raw=True)
        n_entries = int(n_entries)
        self.rplist.set(src, RPL_ENTRY.format(n_entries), val)
        if name != "":
            #name = name.decode('utf-8')
            self.rplist.set(src, RPL_ENTRY_NAME.format(n_entries), name)
        else:
            self.rplist.set(src, RPL_ENTRY_NAME.format(n_entries), val)
        n_entries += 1
        self.rplist.set(src, RPL_NENTRIES, n_entries)
        self.rplistfile = codecs.open(PI_RADIO_LISTS, 'w', encoding='utf-8')
        self.rplist.write(self.rplistfile)
        try:
            self.rplistfile.close()
        except:
            pass


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

            ret = parse.search("add={:w}" + SEPARATOR, cmd)
            if ret is not None and len(ret.fixed) != 0:
                if SRC_MEDIA.lower() == ret.fixed[0].lower():
                    cmd = cmd.replace("add=" + ret.fixed[0], "")
                    self.log.debug("Trying to find media in " + cmd)
                    ret = parse.search(SEPARATOR + "{}" + SEPARATOR, cmd)
                    if ret is not None and len(ret.fixed) != 0:
                        self.log.debug("Trying to parse " + ret.fixed[0])
                        src_type = self.mediaParse(ret.fixed[0])

                        if src_type == SRC_YOUTUBE:
                            self.rplist_add( RPL_YOUTUBE, ret.fixed[0], IRadio.NOW_PLAYING)
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

                # is get playlist
                if CMD_GET_PLAYLIST.lower() == ret.fixed[0].lower():
                    # send the playlist entries
                    n_entries = self.rplist.get(RPL_RADIO, RPL_NENTRIES, raw=True)
                    #if type(n_entries) is str:
                    n_entries = int(n_entries)
                    if n_entries > 0:
                        for idx in range(0,n_entries-1):
                            entry = self.rplist.get(RPL_RADIO, RPL_ENTRY_NAME.format(idx))
                            self.tcpsend.send(FRAME_HEAD + "cmd=radiopls" + SEPARATOR + entry + SEPARATOR + FRAME_TAIL)

                    n_entries = self.rplist.get(RPL_YOUTUBE, RPL_NENTRIES, raw=True)
                    #if type(n_entries) is str:
                    n_entries = int(n_entries)
                    if n_entries > 0:
                        for idx in range(0, n_entries ):
                            entry = self.rplist.get(RPL_YOUTUBE, RPL_ENTRY_NAME.format(idx)).encode('utf-8')
                            self.tcpsend.send(FRAME_HEAD + "cmd=youtbpls" + SEPARATOR + entry + SEPARATOR + FRAME_TAIL)
                    """with open(PI_RADIO_LISTS, 'r') as file:
                        for line in file:
                            if line.startswith("name"):
                                self.tcpsend.send(FRAME_HEAD + "cmd=pls" + SEPARATOR + line + SEPARATOR + FRAME_TAIL )
                    return"""
                # TODO process commands
                # TODO think of a way of saving/managing the added radio stations (local/remote?)
                return

        except Exception as err:
            self.log.error("ERR: Couldn't process message" + err.message)
            pass


class update_now_playing(threading.Thread):
    def __init__(self, threadID, name, logger, radio):
        """

        :param threadID: Thread's ID
        :type threadID: int
        :param name: Thread's name
        :type name: str
        :param logger: the logger
        :type logger: Logger
        :param radio: the display
        :type radio: IRadio

        :return: nothing
        """
        threading.Thread.__init__(self)

        self.log = logger
        self.radio = radio

        self.b_continue = True
        self.now_playing = ""
        self.radio_name = ""
        self.radio_genre = ""
        self.radio_bitrate = ""
        self.active_src = ""
        self.b_is_playing = False

    def run(self):
        # now keep updating
        while self.b_continue:
            try:
                # Check if playback finished
                if self.radio.player.is_playing() != self.b_is_playing:
                    self.b_is_playing = self.radio.player.is_playing()
                    self.radio.display.set_playing_stt(self.b_is_playing)
                    if not self.b_is_playing:
                        IRadio.RADIO_NAME = ""
                        IRadio.NOW_PLAYING = ""
                        IRadio.RADIO_GENRE = ""
                        IRadio.RADIO_BITRATE = ""
                        IRadio.SRC = ""



                # if it's Radio we must keep looking for changes in the STD_OUT
                if self.radio.SRC == SRC_RADIO:
                    while 1:
                        try:    # Try to parse
                            line = self.radio.player.read_stdout()
                            if line.startswith("Name"):
                                self.log.debug("\t\t" + line)
                                IRadio.RADIO_NAME = ""
                                ret = parse.search(": {}\n", line)
                                if ret is not None and len(ret.fixed) != 0:
                                    self.log.debug("Radio Name " + ret.fixed[0])
                                    IRadio.RADIO_NAME = ret.fixed[0]
                            if line.startswith("Genre"):
                                self.log.debug("\t\t" + line)
                                IRadio.RADIO_GENRE = ""
                                ret = parse.search(": {}\n", line)
                                if ret is not None and len(ret.fixed) != 0:
                                    self.log.debug("Radio Genre " + ret.fixed[0])
                                    IRadio.RADIO_GENRE = ret.fixed[0]
                            if line.startswith("Bitrate"):
                                self.log.debug("\t\t" + line)
                                IRadio.RADIO_BITRATE = ""
                                ret = parse.search(": {}\n", line)
                                if ret is not None and len(ret.fixed) != 0:
                                    self.log.debug("Radio Bitrate " + ret.fixed[0])
                                    IRadio.RADIO_BITRATE = ret.fixed[0]
                            if line.startswith('ICY Info:'):
                                self.log.debug("\t\t" + line)
                                IRadio.NOW_PLAYING = ""
                                ret = parse.search("StreamTitle='{}';", line)
                                if ret is not None and len(ret.fixed) != 0:
                                    self.log.debug("sending " + ret.fixed[0])
                                    IRadio.NOW_PLAYING = ret.fixed[0]
                        except Exception as err:
                            break
                    # give the updates to display
                    if self.now_playing != IRadio.NOW_PLAYING:
                        self.now_playing = IRadio.NOW_PLAYING
                        self.radio.display.set_now_playing(self.now_playing)
                    if self.radio_name != IRadio.RADIO_NAME:
                        self.radio_name = IRadio.RADIO_NAME
                        self.radio.display.set_radio_name(self.radio_name)
                    if self.radio_genre != IRadio.RADIO_GENRE:
                        self.radio_genre = IRadio.RADIO_GENRE
                        self.radio.display.set_radio_genre(self.radio_genre)
                    if self.radio_bitrate != IRadio.RADIO_BITRATE:
                        self.radio_bitrate = IRadio.RADIO_BITRATE
                        self.radio.display.set_radio_bitrate(self.radio_bitrate)

                # if we are playing local files
                elif self.radio.SRC == SRC_LOCAL:
                    ret = self.radio.player.get_value(IPlayer.FILENAME)
                    if ret == "":
                        ret = "...nothing playing..."
                    IRadio.NOW_PLAYING = ret

                    # give the updates to display
                    if self.now_playing != IRadio.NOW_PLAYING:
                        self.now_playing = IRadio.NOW_PLAYING
                        self.radio.display.set_now_playing(self.now_playing)

                elif self.radio.SRC == SRC_YOUTUBE:
                    # give the updates to display
                    if self.now_playing != IRadio.NOW_PLAYING:
                        self.now_playing = IRadio.NOW_PLAYING
                        self.radio.display.set_now_playing(self.now_playing)

                # give it a break
                if self.active_src != IRadio.SRC:
                    self.active_src = IRadio.SRC
                    self.radio.display.set_src(self.active_src)
                time.sleep(1)               # Sleep 500ms
            except Exception as err:
                self.log.error("Exception getting now playing: " + err.message)
                pass


def __stop(self):
    try:
        self.b_continue = False
    except Exception as err:
        self.log.error("Excetion stopping thread " + err.message)
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