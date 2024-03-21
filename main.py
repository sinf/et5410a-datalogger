from argparse import ArgumentParser
import traceback
import time
import re
import os
import struct
import sys

import serial as pyserial

the_session_id = struct.unpack('I', os.urandom(4))[0] & 0x7FFFFFFF

class DaadaBasseli:
  def __init__(self, comment=''):
    self.device_id=int(os.environ.get('DEVICE_ID',1))
    self.table=None
    self.co=None
    url = os.environ.get('DBURL')
    if not url:
      print('env DBURL not set, skipping database', file=sys.stderr)
      return
    import sqlalchemy as db
    self.en = db.create_engine(url, pool_pre_ping=True)
    self.co = self.en.connect()
    me = db.MetaData()
    cols = [
        db.Column('time', db.BigInteger(), primary_key=True),
        db.Column('device_id', db.Integer(), nullable=False),
        db.Column('session_id', db.Integer(), nullable=False),
        db.Column('voltage', db.Float(), nullable=False),
        db.Column('current', db.Float(), nullable=False),
        db.Column('energy', db.Float(), nullable=False),
    ]
    self.table = db.Table('dmm_test', me, *cols)
    me.create_all(self.en)
    if comment:
      comment_table=db.Table('dmm_test_comment', me,
        db.Column('session_id', db.Integer(), nullable=False),
        db.Column('comment', db.String(), nullable=False),
      )
      me.create_all(self.en)
      self.co.execute(db.insert(comment_table).values(session_id=the_session_id, comment=comment))
    #self.co.commit()

  def close(self):
    if self.co:
      self.co.close()

  def put(self, volts, current, energy):
    if self.table is None:
      return
    import sqlalchemy as db
    t = int(time.time()*1000) # s -> ms
    values = {
      'time': t,
      'device_id': self.device_id,
      'session_id': the_session_id,
      'voltage': volts,
      'current': current,
      'energy': energy,
    }
    try:
        self.co.execute(db.insert(self.table).values(**values))
        #self.co.commit()
    except db.exc.IntegrityError as e:
        traceback.print_exc()


class DMM:
  def __init__(self, device_path):
    self.eol=b'\n |.\n' # WTF!?
    self.serial = pyserial.serial_for_url(
      device_path,
      9600, # baud rate
      bytesize=8, # one of 5,6,7,8
      parity='N', # one of N E O S M
      stopbits=1, # one of 1 2 3
      rtscts=False, # RTS/CTS flow control
      xonxoff=False, # software flow control
      timeout=1)

  def done(self):
    self.unfuck()
    self.serial.close()

  def unfuck(self):
    # re-enables physical controls
    self.serial.write(self.eol)
    self.serial.write(b'SYST:LOCA' + self.eol)

  def idn(self):
    return self.cmd(b'*IDN?')
# *IDN? output:
# b'ET5410A+ 09702240098 V1.00.2213.016 V1.00.2213.016\r\nRcmd err\r\n'

  def cmd(self, cmd):
    self.serial.reset_input_buffer() # drop Rcmd err
    self.serial.write(cmd+self.eol)
    return self.serial.read_until(b'\r\n', size=200)

  def measure(self):
    x=self.cmd(b'MEAS:ALL?')
# output:
#  b'R 0.089  11.954  1.07  134.046\r\nRcmd err\r\n'
#  amps volts watts ohms
    #print(x)
    if x.startswith(b'R '):
      x=x.replace(b'  ',b' ').split(b' ')
      x=list(filter(lambda x:x!=b'', x))
      i = float(x[1])
      u = float(x[2])
      return u,i
    return ValueError('failed to parse output: ' + str(x))

  def capa():
    # could be more accurate than calculating energy from voltage*current,
    # but this only works in battery test mode (not in any other mode)
    x=self.cmd(b'BATT:CAPA?')
    print(x)
    x=self.cmd(b'BATT:ENER?')
    print(x)


def main():
  ap=ArgumentParser(
    description="This is a data logger script for East Tester 5410A+, a cheap programmable load manufactured in hell. Data is dumped to stdout in csv and into a database too, if env DBURL was set to something that SQL Alchemy accepts",
  )
  ap.add_argument('-p', '--serial-port-device', required=True, help='/dev/ttyUSBsomething')
  ap.add_argument('-d', '--delay', type=float, default=1.0, help='main loop delay in seconds. Should be >0.15, default 1.0')
  ap.add_argument('-s', '--silent', default=False, action='store_true', help='silence csv output to stdout')
  ap.add_argument('-c', '--comment', type=str, default=None, help='add comment on the experiment into additional database table so you know what the collected samples mean')
  ap.add_argument('-i', '--ident-only', default=False, action='store_true')
  args=ap.parse_args()

  dmm=DMM(args.serial_port_device)
  if args.ident_only:
    print(args.serial_port_device, '*IDN? ->', dmm.idn())
    return

  db=DaadaBasseli(comment=args.comment)
  E=0
  p0=None
  t0=None
  output_t=time.time() + args.delay

  csv_file = sys.stdout
  if args.silent:
    csv_file = open('/dev/null', 'w')

  print('time','voltage','current','power','energyJ','energyWh', sep=',', file=csv_file)

  exitcode=1
  try:
    while True:
      time.sleep(0.15)
      try:
        u,i = dmm.measure()
      except:
        traceback.print_exc()
        continue

      p=u*i
      t=time.time()

      if p0 is not None:
        E += (t-t0) * (p0 + p) / 2

      if (u is not None) and t >= output_t:
        output_t += args.delay
        millis=int(t%1*1e3)
        print(f'{time.strftime("%Y-%m-%d %H:%M:%S")}.{millis:03d},{u:.6f},{i:.6f},{p:.6f},{E:.6f},{E/3600:.6f}', file=csv_file)
        db.put(u,i,E)

      t0,p0 = t,p

  except KeyboardInterrupt:
    exitcode=0
  finally:
    dmm.done()
    db.close()

  exit(exitcode)

if __name__=='__main__':
  main()

