import logging
import sys
import threading
import time
import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import IRadio

RST = 24
SCROLL_SPEED = 5

class IDisplay:
    def __init__(self):
        print ""

    def __init__(self, radio):
        self.log = logging.getLogger("IDisplay")
        streamH = logging.StreamHandler(sys.stderr)
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(streamH)
        self.log.debug("IDisplay log inited")

        self.disp_thread = update_display(1, "update_display", self.log, radio)
        self.disp_thread.setDaemon(1)
        self.disp_thread.start()


class update_display(threading.Thread):
    def __init__(self, threadID, name, logger, radio):
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
        self.radio = radio
        self.disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)

        self.disp.begin()
        self.disp.clear()
        self.disp.display()

        self.fontsize_head = 16
        self.font_head = ImageFont.truetype('fonts/vermin_vibes_1989.ttf', self.fontsize_head)       # more fonts in http://www.dafont.com/bitmap.php

        self.fontsize_title = 8
        self.font_title = ImageFont.truetype('fonts/pixelmix.ttf', self.fontsize_title)

        self.image = Image.new('1', (self.disp.width, self.disp.height))

        self.draw = ImageDraw.Draw(self.image)
        self.draw.text((0, 0), "Now playing: ", font=self.font_head, fill=255)
        self.disp.image(self.image)
        self.disp.display()

        self.b_continue = True
        self.now_playing = ""

    def run(self):
        # now keep updating
        b_scroll = False
        xpos = 0
        while self.b_continue:
            try:
                ret = self.radio.get_now_playing()
                if self.now_playing != ret:
                    self.now_playing = ret
                    self.log.debug(">>>>>>>> Now playing: "+self.now_playing+"<<<<<<<<<<")
                    # Write two lines of text.# Draw a black filled box to clear the image.

                    maxwidth, unused = self.draw.textsize(self.now_playing, font=self.font_title)
                    if maxwidth > self.disp.width:
                        xpos = self.disp.width
                        b_scroll = True
                    else:
                        xpos = 0
                        b_scroll = True

                    self.draw.rectangle((0, self.fontsize_head, self.disp.width, self.disp.height-self.fontsize_head),
                                    outline=0, fill=0)
                    self.draw.text((xpos, self.fontsize_head), self.now_playing, font=self.font_title, fill=255)
                    self.disp.image(self.image)
                    self.disp.display()
                time.sleep(0.01)               # Sleep 100ms

                if b_scroll:
                    xpos -= SCROLL_SPEED
                    if -xpos <= maxwidth:
                        self.draw.rectangle((0, self.fontsize_head, self.disp.width, self.disp.height - self.fontsize_head),
                                            outline=0, fill=0)
                        self.draw.text((xpos, self.fontsize_head), self.now_playing, font=self.font_title, fill=255)
                        self.disp.image(self.image)
                        self.disp.display()
                    else:
                        xpos = self.disp.width
            except Exception as err:
                self.log.error("Exception getting now playing: " + err.message)
                pass


    def __stop(self):
        try:
            self.b_continue = False
        except Exception as err:
            log.error("Excetion stopping thread " + err.message)
            pass