#!/usr/bin/python
import time
import logging
import IRadio
import socket
import threading
import atexit
import argparse


#http://www.radyo7.com/dinle/listen.php?ext=pls
#http://7509.live.streamtheworld.com:443/METRO_FM_SC
# init stuffs
log = logging.getLogger("Main")
myRadio = 0 #IRadio.IRadio()
wait_conn_thread = threading.Thread()
HOST = ""
PORT = 6666
BUFF = 1024
FRAME_HEAD = chr(0x02)  #STX
FRAME_TAIL = chr(0x03)  #ETX
TCP_TIMEOUT = 20

class waitTCPConnHandler( threading.Thread):
    def __init__(self, threadID, name):
        """

        :param threadID: Thread's ID
        :type threadID: int
        :param name: Thread's name
        :type name: str

        :return: nothing
        """
        threading.Thread.__init__(self)

        self.threadID = threadID
        self.name = name
        self.comm_thread = threading.Thread()

    def run(self):
        while 1:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                log.info("Socket created")
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # Bind socket to local host and port
                try:
                    self.sock.bind((HOST, PORT))
                except socket.error as msg:
                    log.error("Bind failed. Error Code: {0} Message: {1}".format(msg[0], msg[1]))
                    time.sleep(1)   # rest a second
                    continue

                log.info("Socket bind complete")

                # Start listening on socket
                self.sock.listen(10)
                log.info("Socket now listening in port {0}".format(PORT))
                # now keep talking with the client
                while 1:
                    try:
                        # wait to accept a connection - blocking call
                        conn, addr = self.sock.accept()
                        # log.info("Connected with {0} : {1}".format(addr[0], str(addr[1])))
                        # thread.start_new_thread(get_tcp_cmds_handler, (conn,))
                        self.comm_thread = getTCPCmdsHandler(1, "comm_thread", conn)
                        self.comm_thread.start()
                    except Exception as err:
                        log.error("Failed accepting connection: " + err.message)
                        break   # try to bing again

                self.comm_thread.__stop()
                self.sock.close()
            except Exception as err:
                log.error("Error in bind: " + err.message + "\nTrying again!")
                time.sleep(1)   # rest a second
                continue


    def __stop(self):
        try:
            log.info("Stopping " + self.name)
            self.comm_thread.__stop()
            self.sock.close()
        except Exception as err:
            log.error("Excetion stopping thread " + err.message)
            pass


class getTCPCmdsHandler (threading.Thread):
    def __init__(self, threadID, name, clientsock):
        """

        :param threadID: Thread's ID
        :type threadID: int
        :param name: Thread's name
        :type name: str
        :param clientsock: The socket to read/write
        :type clientsock: socket._socketobject

        :return: nothing
        """
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.clientsock = clientsock
        self.b_stop = False

    def run(self):
        global myRadio
        self.clientsock.setblocking(0)
        frame = ""
        log.info("Waiting messages from TCP...\n")
        while not self.b_stop:
            log.debug("waiting new frame...\n")
            frame = ""
            b_frame = False
            begin = time.time()
            while not b_frame:
                if frame != "" and time.time() - begin > TCP_TIMEOUT * 2:
                    log.info("TimeOut and some data " + frame )
                    frame = ""
                try:
                    data = self.clientsock.recv(1)
                    if data:
                        frame += data
                        if frame.startswith(FRAME_HEAD) and frame.endswith(FRAME_TAIL):
                            log.debug("frame COMPLETE")
                            b_frame = True
                        elif not frame.startswith(FRAME_HEAD[0]) and len(frame) > len(FRAME_HEAD):
                            log.debug("INVALID head")
                            frame = ""
                        # change the beginning time for measurement
                        begin = time.time()
                    else:
                        # sleep for sometime to indicate a gap
                        time.sleep(0.1)
                except:
                    # comes here always that there's no data received, which is most of the time, so lets give it a rest
                    # since we aren't getting any data anyway
                    time.sleep(0.1)
                    pass
            log.info("Going to process " + frame)
            myRadio.process_command(frame)

        self.clientsock.close()

    def __stop(self):
        log.info("Stopping " + self.name)
        self.b_stop = True


def __init__(nodisp=False, cmd_prearg=""):
    global myRadio
    streamH = logging.StreamHandler(sys.stdout)
    log.addHandler(streamH)
    log.setLevel(logging.DEBUG)


    myRadio = IRadio.IRadio(nodisp=nodisp, prearg=cmd_prearg)
    myRadio.mediaParse("http://7509.live.streamtheworld.com:443/METRO_FM_SC")
    wait_conn_thread = waitTCPConnHandler(1, "wait_conn_thread")
    wait_conn_thread.setDaemon(1)
    wait_conn_thread.start()

    try:
        while 1:
            time.sleep(10)
            pass
    except (KeyboardInterrupt, SystemExit):
        log.info("SIG_TERM received")
    # it will remain here as long as wait_conn_thread isn't terminated
    log.info("Exiting main thread...")


def at_exit():
    try:
        myRadio.stop()
    except Exception as err:
        print err.message
        pass
    log.info("exiting...")
    if wait_conn_thread.isAlive():
        log.info("killing...")
        wait_conn_thread.__stop()
        wait_conn_thread.join()


# In case is called from terminal
if __name__ == "__main__":
    import sys
    # register the program exit
    atexit.register(at_exit)

    # process arguments
    args_parse = argparse.ArgumentParser(description="radioPi args")
    #args_parse.add_argument('--player', help="The media player command (default omxplayer)")
    args_parse.add_argument('--prearg', help="Argument to put before player call (e.g. torify for allowing playing radios at work :P)")
    args_parse.add_argument('--ip', help="The IP to allow connection (default {0})".format(HOST))
    args_parse.add_argument('--port', help="The port to listen (default {0})".format(PORT))
    args_parse.add_argument('--nodisp', help="Disable the usage of OLED SSD1306/9 1->disable (default 0)")
    args = args_parse.parse_args()

    nodisp = False  # by default we use display
    prearg = ""     # by default no pre argument

    # if another player was passed as argument
    #if args.player is not None:
    #    myRadio = IRadio.IRadio(args.player)
    if args.prearg is not None:
        prearg = args.prearg
    if args.ip is not None:
        HOST = args.ip
    if args.port is not None:
        try:
            PORT = int(args.port)
        except Exception as ex:
            print("The Port must be integer" + ex.message)
            exit()
    if args.nodisp is not None:
        if args.nodisp == "1":
            nodisp = True
            print("Disabling OLED display")
        elif args.nodisp != "0":
            print("{0} is an invalid argument for --nodisp. Valid values are 0 and 1".format(args.nodisp))
            exit()
    __init__( nodisp, prearg )



