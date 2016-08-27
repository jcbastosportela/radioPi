# radioPi

Just because I need to plug my Pi as an Internet Radio to my amplifier without having to open my TV to manage what I'm listening.


.Requires:
youtube_dl
parse
ConfigParser

.TCP protocol:
src=SRC[link|url|pls]=CONTENT

.Examples of radio links:
src=radiourl=mms://195.245.168.21/antena1
src=radiolink=http://radyo.itu.edu.tr/ITU_Radio_Rock.pls
src=radiolink=http://radyo.itu.edu.tr/ITU_Radio_Jazz_Blues.pls
src=radiolink=http://radyo.itu.edu.tr/ITU_Radio_Classical.pls
src=radiourl=http://voyagewmp.radyotvonline.com
src=mediahttps://www.youtube.com/watch?v=wDjeBNv6ip0
src=media/home/porty/Music/TUGAS/Carlos Paiao - Cinderela.mp3
src=media/home/porty/Music/TUGAS

.Example of control commands:
ctrl=play
ctrl=stop
ctrl=volup
ctrl=voldown

.Example of commands:
cmd=listradios
cmd=gpls

src=mediahttp://37.247.98.10/
