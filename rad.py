#!/usr/bin/python
import time
import logging
import IRadio
import socket
import thread
import atexit


#http://www.radyo7.com/dinle/listen.php?ext=pls
#http://7509.live.streamtheworld.com:443/METRO_FM_SC
# init stuffs
log = logging.getLogger("Main")
RAD_CMD = "omxplayer"
myRadio = IRadio.IRadio()
sock = socket.socket()
HOST = ""
PORT = 6666
BUFF = 1024
FRAME_HEAD = chr(0x02)  #STX
FRAME_TAIL = chr(0x03)  #ETX
TCP_TIMEOUT = 20


def get_tcp_cmds_handler(clientsock):
    """

    :param clientsock: The socket to listen
    :type clientsock: socket._socketobject

    :return: nothing
    """
    clientsock.setblocking(0)
    frame = ""
    log.info("Waiting messages from TCP...\n")
    while 1:
        log.debug("waiting new frame...\n")
        frame = ""
        b_frame = False
        begin = time.time()
        while not b_frame:
            if frame != "" and time.time() - begin > TCP_TIMEOUT * 2:
                log.info("TimeOut and some data " + frame )
                frame = ""
            try:
                data = clientsock.recv(1)
                if data:
                    log.debug("got a bit " + data)
                    frame += data
                    log.debug("the frame is now " + frame)
                    if frame.startswith(FRAME_HEAD) and frame.endswith(FRAME_TAIL):
                        log.debug("frame COMPLETE")
                        b_frame = True
                    elif not frame.startswith(FRAME_HEAD):
                        log.debug("INVALID head")
                        if len(frame) >= len(FRAME_HEAD):
                            log.debug("... longer than head")
                            if FRAME_HEAD not in frame:
                                log.debug("... No FRAME_HEAD found")
                                frame = ""
                            else:
                                trash, value = frame.split(FRAME_HEAD, 1)
                                frame = FRAME_HEAD + value
                                log.debug("... FRAME_HEAD found " + frame)
                    # change the beginning time for measurement
                    begin = time.time()
                else:
                    # sleep for sometime to indicate a gap
                    time.sleep(0.1)
            except:
                pass
        log.info("Going to process " + frame)
        myRadio.process_command(frame)


def __init__():
    import sys
    streamH = logging.StreamHandler(sys.stdout)
    log.addHandler(streamH)
    log.setLevel(logging.DEBUG)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    log.info("Socket created")
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Bind socket to local host and port
    try:
        sock.bind((HOST, PORT))
    except socket.error as msg:
        log.error("Bind failed. Error Code : {0} Message {1}".format(msg[0], msg[1]))
        sys.exit()

    log.info("Socket bind complete")

    # Start listening on socket
    sock.listen(10)
    log.info("Socket now listening")

    #myRadio = IRadio.IRadio(get_video_url("https://www.youtube.com/watch?v=hn3wJ1_1Zsg"))
    myRadio.play("http://7509.live.streamtheworld.com:443/METRO_FM_SC")

    # now keep talking with the client
    while 1:
        # wait to accept a connection - blocking call
        conn, addr = sock.accept()
        #log.info("Connected with {0} : {1}".format(addr[0], str(addr[1])))
        thread.start_new_thread(get_tcp_cmds_handler, (conn,))

    sock.close()


def at_exit():
    log.info("exiting...")
    if sock is not None:
        sock.close()


# In case is called from terminal
if __name__ == "__main__":
    import sys

    # register the program exit
    atexit.register(at_exit)
    # the only argument acceptable is another player
    if len(sys.argv) >= 2:
        myRadio = IRadio.IRadio(sys.argv[1])
    __init__()



