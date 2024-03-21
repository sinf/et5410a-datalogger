from argparse import ArgumentParser
import serial as pyserial
import time

# the poor thing locks up if anyone opens the serial port
# this script fixes it

ap=ArgumentParser()
ap.add_argument('-p', '--port', required=True)
args=ap.parse_args()

serial = pyserial.serial_for_url(
  args.port,
  9600, # baud rate
  bytesize=8, # one of 5,6,7,8
  parity='N', # one of N E O S M
  stopbits=1, # one of 1 2 3
  rtscts=False, # RTS/CTS flow control
  xonxoff=False, # software flow control
  timeout=1)

eol=b'\n |.\n' # WTF!?

serial.write(eol)
time.sleep(0.15)
serial.reset_input_buffer()

for i in range(2):
  serial.write(b'SYST:LOCA'+eol)
  print(serial.read_until('\r\n'))
  time.sleep(0.15)

serial.close()

