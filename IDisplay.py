import threading
import time
import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import IRadio


RST = 24

class IDisplay:
    def __init__(self):
        self.disp_thread = update_display(1, "update_display")
        self.disp_thread.setDaemon(1)
        self.disp_thread.start()
        print ""


class update_display(threading.Thread):
    def __init__(self, threadID, name):
        """

        :param threadID: Thread's ID
        :type threadID: int
        :param name: Thread's name
        :type name: str

        :return: nothing
        """
        self.disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)

        self.disp.begin()
        self.disp.clear()
        self.disp.display()

        #self.font = ImageFont.load_default()
        self.font = ImageFont.truetype('pixelmix.ttf', 8)       # more fonts in http://www.dafont.com/bitmap.php
        self.image = Image.new('1', (self.disp.width, self.disp.height))
        self.draw = ImageDraw.Draw(self.image)

        #if self.disp.height == 64:
        #    self.image = Image.open('happycat_oled_64.ppm').convert('1')
        #else:
        #    self.image = Image.open('happycat_oled_32.ppm').convert('1')
        #self.disp.image(self.image)
        #self.disp.display()
        threading.Thread.__init__(self)
        self.b_continue = True
        self.now_playing = ""

    def run(self):
        # now keep updating
        while self.b_continue:
            print "!!!!!!!!"
            if self.now_playing != IRadio.get_now_playing():
                self.now_playing = IRadio.get_now_playing()
                print(">>>>>>>>"+self.now_playing+"<<<<<<<<<<")
                # Write two lines of text.# Draw a black filled box to clear the image.
                self.draw.rectangle((0, 0, self.disp.width, self.disp.height), outline=0, fill=0)
                self.draw.text((10, 10), self.now_playing, font=self.font, fill=255)
                self.disp.image(self.image)
                self.disp.display()
            time.sleep(1)               # Sleep 100ms

    def __stop(self):
        try:
            self.b_continue = False
        except Exception as err:
            log.error("Excetion stopping thread " + err.message)
            pass