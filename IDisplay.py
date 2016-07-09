
class IDisplay:
    def __init__(self):
        nowPlaying = ""
        print ""

    def setNowPlaying(self, _nowPlaying):
        """
        Sets the now playing song in the display
        :param nowPlaying: The media playing currently
        :type nowPlaying: str
        :return: none
        """
        self.nowPlaying = _nowPlaying
        print self.nowPlaying