from argparse import ArgumentParser
import serial as pyserial
import time
import re

# East Tester 5410A+, the cheap programmable load straight from hell.
# This piece of junk is bit quirky

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

def unfuck():
  serial.write(b'SYST:LOCA'+eol)

def idn():
  serial.write(b'*IDN?' + eol)
  time.sleep(0.15)
  x=serial.readall()
  print(x)
# output:
# b'ET5410A+ 09702240098 V1.00.2213.016 V1.00.2213.016\r\nRcmd err\r\n'

def measure():
  serial.reset_input_buffer() # drop Rcmd err
  serial.write(b'MEAS:ALL?'+eol)
  x=serial.read_until(b'\r\n', size=200)
# output:
#  b'R 0.089  11.954  1.07  134.046\r\nRcmd err\r\n'
#  amps volts watts ohms
  print(x)
  if x.startswith(b'R '):
    x=x.split(b'  ')
    u = float(x[0][2:])
    i = float(x[1])
    return u,i

try:
  for i in range(100):
    u,i = measure()
    print(u,i)
    time.sleep(0.15)
finally:
  unfuck()
  serial.close()

