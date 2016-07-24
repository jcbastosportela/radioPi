import logging
import sys
import threading
import time
import IRadio
try:
    import Adafruit_SSD1306
    from PIL import Image
    from PIL import ImageDraw
    from PIL import ImageFont
except:
    pass

RST = 24
SCROLL_SPEED = 5
NOW_PLAYING_TXT = "Now playing: "
DETAILS_TXT = "Details: "

class IDisplay:
    NOW_PLAYING = ""
    RADIO_NAME = ""
    RADIO_GENRE = ""
    RADIO_BITRATE = ""
    SRC = ""
    IS_PLAYING = False
    def __init__(self):
        """

        :param radio: the client class IRadio
        :type radio: IRadio.IRadio
        :return nothing
        """
        self.log = logging.getLogger("IDisplay")
        streamH = logging.StreamHandler(sys.stderr)
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(streamH)
        self.log.debug("IDisplay log inited")

        self.disp_thread = update_display(1, "update_display", self.log)
        self.disp_thread.setDaemon(1)
        self.disp_thread.start()

    def set_now_playing(self, title):
        IDisplay.NOW_PLAYING = title

    def set_radio_name(self, name):
        IDisplay.RADIO_NAME = name

    def set_radio_genre(self, genre):
        IDisplay.RADIO_GENRE = genre

    def set_radio_bitrate(self, br):
        IDisplay.RADIO_BITRATE = br

    def set_src(self, src):
        IDisplay.SRC = src

    def set_playing_stt(self, b_stt):
        IDisplay.IS_PLAYING = b_stt


class update_display(threading.Thread):
    def __init__(self, threadID, name, logger):
        """

        :param threadID: Thread's ID
        :type threadID: int
        :param name: Thread's name
        :type name: str
        :param logger: the logger
        :type logger: Logger

        :return: nothing
        """
        threading.Thread.__init__(self)

        self.log = logger
        self.disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)

        self.disp.begin()
        self.disp.clear()
        self.disp.display()

        self.fontsize_head = 16
        self.font_head = ImageFont.truetype('/home/pi/radio/fonts/vermin_vibes_1989.ttf', self.fontsize_head)       # more fonts in http://www.dafont.com/bitmap.php

        self.fontsize_title = 8
        self.font_title = ImageFont.truetype('/home/pi/radio/fonts/pixelmix.ttf', self.fontsize_title)

        self.fontsize_details = 16
        self.font_details = ImageFont.truetype('/home/pi/radio/fonts/vermin_vibes_1989.ttf', self.fontsize_details)

        self.image = Image.new('1', (self.disp.width, self.disp.height))

        self.draw = ImageDraw.Draw(self.image)
        self.draw.text((0, 0), NOW_PLAYING_TXT, font=self.font_head, fill=255)
        self.draw.text((0, self.fontsize_head + self.fontsize_title), DETAILS_TXT, font=self.font_details, fill=255)
        self.disp.image(self.image)
        self.disp.display()

        self.b_continue = True
        self.now_playing = ""
        self.radio_name = ""
        self.radio_genre = ""
        self.radio_bitrate = ""
        self.active_src = ""
        self.b_is_playing = False

    #def show_animation(self):
        #image = []
        #for each frame in image:
        #    print""

    def run(self):
        #self.show_animation()
        # now keep updating
        b_scrl_title = False
        b_scrl_rname = False
        xpos_title = 0
        xpos_rname = 0
        y_rname = self.fontsize_head + self.fontsize_title + self.fontsize_details
        y_rgen = y_rname + self.fontsize_title
        y_src = self.fontsize_head + self.fontsize_title
        xpos_src, unused = self.draw.textsize(DETAILS_TXT, font=self.font_details)
        xpos_src += 3
        while self.b_continue:
            try:
                if self.radio_name != IDisplay.RADIO_NAME or self.radio_bitrate != IDisplay.RADIO_BITRATE:
                    self.radio_name = IDisplay.RADIO_NAME
                    self.radio_bitrate = IDisplay.RADIO_BITRATE
                    self.log.debug(">>>>>>>> Radio Name: " + self.radio_name + "<<<<<<<<<<")

                    txt =  self.radio_name
                    if IDisplay.RADIO_BITRATE != "":
                        txt += " @" + IDisplay.RADIO_BITRATE

                    maxW_rname, unused = self.draw.textsize(txt, font=self.font_title)
                    if maxW_rname > self.disp.width:
                        xpos_rname = self.disp.width
                        b_scrl_rname = True
                    else:
                        xpos_rname = 0
                        b_scrl_rname = False

                    self.draw.rectangle((0, y_rname, self.disp.width, y_rname + self.fontsize_title),
                                        outline=0, fill=0)
                    self.draw.text((0, y_rname), txt , font=self.font_title, fill=255)
                    self.disp.image(self.image)
                    self.disp.display()

                if self.active_src != IDisplay.SRC:
                    self.active_src = IDisplay.SRC
                    self.log.debug("!!!!!!!! Source: " + self.active_src + "!!!!!!!!!!")

                    self.draw.rectangle((xpos_src, y_src, self.disp.width, y_src + self.fontsize_details),
                                        outline=0, fill=0)
                    self.draw.text((xpos_src, y_src), self.active_src, font=self.font_title, fill=255)
                    self.disp.image(self.image)
                    self.disp.display()

                if self.radio_genre != IDisplay.RADIO_GENRE:
                    self.radio_genre = IDisplay.RADIO_GENRE
                    self.log.debug(">>>>>>>> Radio Genre: " + self.radio_genre + "<<<<<<<<<<")

                    self.draw.rectangle((0, y_rgen, self.disp.width, y_rgen + self.fontsize_details),
                                        outline=0, fill=0)
                    self.draw.text((0, y_rgen), self.radio_genre, font=self.font_title, fill=255)
                    self.disp.image(self.image)
                    self.disp.display()

                if self.now_playing != IDisplay.NOW_PLAYING:
                    self.now_playing = IDisplay.NOW_PLAYING
                    self.log.debug(">>>>>>>> Now playing: "+self.now_playing+"<<<<<<<<<<")
                    # Write two lines of text.# Draw a black filled box to clear the image.

                    maxW_title, unused = self.draw.textsize(self.now_playing, font=self.font_title)
                    if maxW_title > self.disp.width:
                        xpos_title = self.disp.width
                        b_scrl_title = True
                    else:
                        xpos_title = 0
                        b_scrl_title = False

                    self.draw.rectangle( (0, self.fontsize_head, self.disp.width, self.fontsize_title + self.fontsize_head),
                                    outline=0, fill=0)
                    self.draw.text((xpos_title, self.fontsize_head), self.now_playing, font=self.font_title, fill=255)
                    self.disp.image(self.image)
                    self.disp.display()

                if b_scrl_title or b_scrl_rname:
                    if b_scrl_title:
                        xpos_title -= SCROLL_SPEED
                        if -xpos_title <= maxW_title:
                            self.draw.rectangle((0, self.fontsize_head, self.disp.width, self.fontsize_title+self.fontsize_head),
                                                outline=0, fill=0)
                            self.draw.text((xpos_title, self.fontsize_head), self.now_playing, font=self.font_title, fill=255)
                        else:
                            xpos_title = self.disp.width

                    if b_scrl_rname:
                        xpos_rname -= SCROLL_SPEED*2
                        if -xpos_rname <= maxW_rname:
                            self.draw.rectangle((0, y_rname, self.disp.width, y_rname + self.fontsize_title),
                                                    outline=0, fill=0)
                            self.draw.text((xpos_rname, y_rname), txt, font=self.font_title, fill=255)
                        else:
                            xpos_rname = self.disp.width

                    self.disp.image(self.image)
                    self.disp.display()
                    time.sleep(0.01)  # Sleep 100ms
                else:
                    time.sleep(0.5)  # Sleep 100ms

                if self.b_is_playing != IDisplay.IS_PLAYING:
                    self.b_is_playing = IDisplay.IS_PLAYING
                    if not self.b_is_playing:
                        self.log.debug("Playback stopped...")
                        IDisplay.RADIO_NAME = ""
                        IDisplay.NOW_PLAYING = ""
                        IDisplay.RADIO_GENRE = ""
                        IDisplay.RADIO_BITRATE = ""
                        IDisplay.SRC = ""
            except Exception as err:
                self.log.error("Exception getting now playing: " + err.message)
                pass


    def __stop(self):
        try:
            self.b_continue = False
        except Exception as err:
            log.error("Excetion stopping thread " + err.message)
            pass

class IDisplay_fake:
    def __init__(self):
        """

        :param radio: the client class IRadio
        :type radio: IRadio.IRadio
        :return nothing
        """
        self.log = logging.getLogger("IDisplay")
        streamH = logging.StreamHandler(sys.stderr)
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(streamH)
        self.log.debug("IDisplay log inited")

        self.disp_thread = update_fake_display(1, "update_display", self.log)
        self.disp_thread.setDaemon(1)
        self.disp_thread.start()

    def set_now_playing(self, title):
        IDisplay.NOW_PLAYING = title

    def set_radio_name(self, name):
        IDisplay.RADIO_NAME = name

    def set_radio_genre(self, genre):
        IDisplay.RADIO_GENRE = genre

    def set_radio_bitrate(self, br):
        IDisplay.RADIO_BITRATE = br

    def set_src(self, src):
        IDisplay.SRC = src

    def set_playing_stt(self, b_stt):
        IDisplay.IS_PLAYING = b_stt

class update_fake_display(threading.Thread):
    def __init__(self, threadID, name, logger):
        """

        :param threadID: Thread's ID
        :type threadID: int
        :param name: Thread's name
        :type name: str
        :param logger: the logger
        :type logger: Logger

        :return: nothing
        """
        threading.Thread.__init__(self)

        self.log = logger
        self.b_continue = True
        self.now_playing = ""

    def run(self):
        # now keep updating
        while self.b_continue:
            try:
                if self.now_playing != IDisplay.NOW_PLAYING:
                    self.now_playing = IDisplay.NOW_PLAYING
                    self.log.debug(">>>>>>>> Now playing: "+self.now_playing+"<<<<<<<<<<")
                time.sleep(1)               # Sleep 1000ms
            except Exception as err:
                self.log.error("Exception getting now playing: " + err.message)
                pass


    def __stop(self):
        try:
            self.b_continue = False
        except Exception as err:
            log.error("Excetion stopping thread " + err.message)
            pass
