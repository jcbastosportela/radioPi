import threading


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


class update_display(threading.Thread):
    def __init__(self, threadID, name, sock):
        """

        :param threadID: Thread's ID
        :type threadID: int
        :param name: Thread's name
        :type name: str
        :param sock: The socket to wait connections
        :type sock: socket

        :return: nothing
        """
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.sock = sock
        self.comm_thread = threading.Thread()

    def run(self):
        # now keep talking with the client
        while 1:
            # wait to accept a connection - blocking call
            conn, addr = self.sock.accept()
            # log.info("Connected with {0} : {1}".format(addr[0], str(addr[1])))
            # thread.start_new_thread(get_tcp_cmds_handler, (conn,))
            self.comm_thread = getTCPCmdsHandler(1, "comm_thread", conn)
            self.comm_thread.start()

    def __stop(self):
        try:
            log.info("Stopping " + self.name)
            self.comm_thread.__stop()
            self.sock.close()
        except Exception as err:
            log.error("Excetion stopping thread " + err.message)
            pass