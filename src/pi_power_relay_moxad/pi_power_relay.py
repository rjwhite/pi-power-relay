"""pi-power-relay

see if host(s) on an outside network are reachable via ping.
If not, reset a device, likely a modem, that is known to be flakey,
by power cycling it via a power relay.

This is intended to be run on a Raspberry Pi, using an 'IoT Power Relay
version 2' from Digital Loggers, to use GPIO to power-cycle a device.
The power relay is plugged into a UPS, while the Raspberry Pi is plugged
into the 'always ON' power port and the modem is plugged into the
'normally ON' power port.  The program, when detecting a loss of network
connectivity, will drop power on the 'normally ON' port, and bring it 
back after a short period.  See the product it uses at:
  https://dlidirect.com/products/iot-power-relay
Typically run from the cron every couple of minutes.

If run on something other than a Raspberry Pi, it will assume it is
a development or test box and will NOT do the actual shutdown, but
will still do everything else.  On the Raspberry Pi, you will need the
RPi.GPIO module installed, by either doing a:
    sudo apt-get install rpi.gpio
on a Debian based Linux box, or installing from the Python Package Index:
        pip install RPi.GPIO
This module will only be imported if run on a Raspberry Pi.

There is an option called -e or --delay-exit, which may not be clear why.
The reason for this is that if you do not use the --quiet option, then
an informational message is printed out before the program exits.  But if
you are relying on ouput from the crontab to then be sent to you on some
other machine via e-mail, it will fail if you do not have a full blown
mailer set up that queues the message, and the DNS lookup for the
destination will fail because the device (modem?) has not
recovered yet.  So, this delay will give the device time to recover,
before you spit out the message and then exit.
The default is no delay.  A good value to use would be 180 seconds.
"""

import os
import sys
import time
import re
import getpass

from . import __version__
from .globals import progname, debug_flag
from .functions import *


def die( error ):
    """print an error message and exit

    Arguments:
        1:  message
    Globals:
        globals.progname
    """

    if globals.progname == None:
        prefix = ''
    else:
        prefix = globals.progname + ': '

    sys.stderr.write( "{}{}\n".format( prefix, error ))
    sys.exit(1)


# main
#
# Arguments:
#   command-line arguments
# Returns:
#   0:  ok
#   1:  not ok
# Exceptions:
#   none

def main( argv=sys.argv ):
    """main program

    use -h or --help for command line options

    Returns:
        0:  ok
        1:  not ok
    """

    progname = argv[0]
    if progname == None or progname == "":
        progname = 'pi_power_relay'

    globals.progname = progname     # make available to other functions

    # see if we are running on a raspberry Pi
    HAVE_GPIO = False
    if os.uname()[4].lower().startswith( 'arm' ):
        HAVE_GPIO = True

    # values that can be changed via options

    pin_number       = 25            # GPIO pin number
    reset_time       = 15            # between setting pin HIGH, then LOW
    wait_time        = 10 * 60       # wait time to reset again 
    ping_timeout     = 2             # secs to wait for ping to time out
    ping_tries       = 3             # number of pings to try
    delay_exit_wait  = 0             # delay before output message and exit
    device_name      = 'device'      # use device name in log message
    log_file         = ""            # LOG file.  none by default
    maint_times      = []            # array of maint times HH:MM-HH:MM
    quiet_flag       = False
    force_flag       = False
    help_flag        = False
    logging_flag     = False
    dns_hosts        = [ '8.8.4.4', '8.8.8.8' ]
    lock_file        = "/tmp/pi-power-relay--reset-time"

    # limits

    max_reset_time   = 60
    max_wait_time    = 30 * 60
    max_ping_timeout = 10
    max_ping_tries   = 10

    # get options

    num_args = len( argv )
    i = 1
    while i < num_args:
        try:
            arg = argv[i]
            if arg == '-d' or arg == '--debug':
                globals.debug_flag = True
            elif arg == '-h' or arg == '--help':
                help_flag = True
            elif arg == '-f' or arg == '--force-reset':
                force_flag = True
            elif arg == '-q' or arg == '--quiet':
                quiet_flag = True
            elif arg == '-r' or arg == '--reset-time':
                i = i + 1 ; val = argv[i]
                if is_int( val ) == False:
                    die( "Not an integer: \'{0:s}\'".format( val ))
                if ( num_too_big( int( val ), max_reset_time )):
                    die( "reset time too large ({:s} > {:d})". \
                        format( val , max_reset_time ))
                reset_time = int( val )
            elif arg == '-w' or arg == '--wait-time':
                i = i + 1 ; val = argv[i]
                if is_int( val ) == False:
                    die( "Not an integer: \'{:s}\'".format( val ))
                if ( num_too_big( int( val ), max_wait_time )):
                    die( "wait time too large ({:s} > {:d})". \
                        format( val, max_wait_time ))
                wait_time = int( val )
            elif arg == '-m' or arg == '--maint':
                i = i + 1
                maint_times.append( argv[i] )
            elif arg == '-t' or arg == '--tries':
                i = i + 1 ; val = argv[i]
                if is_int( val ) == False:
                    die( "Not an integer: \'{0:s}\'".format( val ))
                if ( num_too_big( int( val ), max_ping_tries )):
                    die( "num ping tries too large ({:s} > {:d})". \
                        format( val, max_ping_tries ))
                ping_tries = int( val )
            elif arg == '-e' or arg == '--delay-exit':
                i = i + 1 ; val = argv[i]
                if is_int( val ) == False:
                    die( "Not an integer: \'{0:s}\'".format( val ))
                delay_exit_wait = int( val )
            elif arg == '-x' or arg == '--ping-timeout':
                i = i + 1 ; val = argv[i]
                if is_int( val ) == False:
                    die( "Not an integer: \'{0:s}\'".format( val ))
                if ( num_too_big( int( val ), max_ping_timeout )):
                    die( "ping timeout too large ({:s} > {:d})". \
                        format( val, max_ping_timeout ))
                ping_timeout = int( val )
            elif arg == '-p' or arg == '--pin':
                i = i + 1 ; val = argv[i]
                if is_int( val ) == False:
                    die( "Not an integer: \'{0:s}\'".format( val ))
                val = int( val )
                if ( val > 27 ) or ( val < 0 ):
                    die( "invalid pin num: \'{}\'".format( val ))
                pin_number = val
            elif arg == '-D' or arg == '--device-name':
                i = i + 1 ; device_name = argv[i]
            elif arg == '-L' or arg == '--lockfile':
                i = i + 1 ; lock_file = argv[i]
            elif arg == '-l' or arg == '--logfile':
                i = i + 1 ; log_file = argv[i]
                logging_flag = True
            elif arg == '-H' or arg == '--hosts' or arg == '--dns-hosts':
                # permit --hosts for backward compatibility
                i = i + 1 ; val = argv[i]
                dns_hosts = val.split( "," )
            elif arg == '-V' or arg == '--version':
                print( "version: {0}".format( __version__ ))
                return(0)
            else:
                m = re.match( "^\-", arg )
                if m:
                    die( "unknown option: \'%s\'" % arg )
                else:
                    die( "unknown option: \'%s\'" % arg )

        except IndexError as err:
            msg = "Missing argument value to \'{0:s}\'?".format( arg )
            die( "%s.  %s" %  ( str(err), msg ))

        i = i+1

    # now that we have processed all our options, our usage can show
    # defaults properly

    if help_flag:
        print( "usage: {} [options]*".format( sys.argv[0] ))

        options = """\
        [-d|--debug]               debugging output
        [-e|--delay-exit num]      delay time before output and exit ({} secs)
        [-f|--force-reset]         reset now and quit, despite state or lock
        [-h|--help]                print this help info
        [-l|--logfile string]      log filename (none by default)
        [-m|--maint HH:MM-HH:MM]*  Maintenance time to NOT reset (none by default)
        [-p|--pin num ]            GPIO pin number ({})
        [-q|--quiet]               supress informational messages
        [-r|--reset-time num]      wait time between GPIO state change ({} secs)
        [-t|--tries num]           max number of ping attempts per host ({})
        [-w|--wait-time num]       reset wait time after previous reset ({} secs)
        [-x|--ping-timeout num]    wait time for ping to time out ({} secs)
        [-D|--device-name string]  name of thing being reset for log ({})
        [-H|--dns-hosts string(s)] comma-delimited hosts to ping ({})
        [-L|--lockfile string]     lock-file ({})
        [-V|--version]             print version of this program ({})\
        """
        print( options.format( delay_exit_wait, pin_number, reset_time,
            ping_tries, wait_time, ping_timeout, device_name,
            ','.join( dns_hosts ), lock_file, __version__ ))

        return(0)

    # if we were given any maintenance time intervals
    if len( maint_times ):
        current_time = time.localtime( None )
        c_total_mins = current_time[3] * 60 + current_time[4]
        dprint( "Current number of minutes into today is {0:d}". \
            format( c_total_mins ))

        for maint_str in maint_times:
            try:
                ( maint_start, maint_end ) = convert_times( maint_str )
            except Exception as err:
                die( err )
            dprint( "maint start={0:d}, end={1:d} (mins) for period {2:s}". \
                format( maint_start, maint_end, maint_str ))

            if ( c_total_mins > maint_start ) and ( c_total_mins < maint_end ):
                dprint( "now in maintenance interval of {0:s}.  Quitting.". \
                    format( maint_str ))
                return(0)
            else:
                dprint( "not in maintenance interval of %s." % maint_str )

    # See if we are running on our target Raspberry pi.
    # Anything else will be a development or test environment

    if HAVE_GPIO == True:
        dprint( "Running on a Raspberry Pi." )

        # need to be root for access to memory
        if getpass.getuser() != 'root':
            die( "Need to be root to use GPIO" )
    else:
        # development/debugging code
        dprint( "I'm NOT running on a Raspberry Pi (" + os.uname()[4] + ")"  )
        dprint( "Assuming a development/test box - will NOT shutdown device" )

    # see if the network still reachable

    state = test_network( dns_hosts, ping_tries, ping_timeout )
    if state:
        # still up
        dprint( "Nothing to do. All is well.  exiting." )
        return(0)

    # see if the device is locked from a recent reset
    device_locked = False
    try:
        device_locked = is_reset_locked( lock_file, wait_time )
    except Exception as err:
        pass

    if device_locked:
        dprint( "found a timing lock: %s" % lock_file )
        # the device is locked from resetting
        if force_flag == False:
            dprint( "timing lock in effect.  skipping the reset" )
            return(0)
        else:
            # force the reset despite the lock
            dprint( "over-riding device timing lock because of force flag" )
    else:
        dprint( "no device timing lock found" )

    # ok, let's do it...
    if ( logging_flag ):
        msg = "{0:s}: network unreachable.  resetting {1:s}\n". \
            format( progname, device_name )
        try:
            logit( log_file, msg )
        except Exception as err:
            sys.stderr.write( "%s: %s\n" % ( progname, err ))
            # keep going

    # been long enough since last reset.  do it now
    try:
        vals = { 'quiet-flag': quiet_flag, 'device-name': device_name }
        reset_device( pin_number, reset_time, lock_file, vals, HAVE_GPIO )
    except Exception as err:
        sys.stderr.write( "%s: error resetting device: %s\n" % \
            ( progname, err ))
        # keep going

    # Informational message to print
    # Get the real time first before a potential delay exit

    msg = "{0:s} reset at {1:s}". \
        format( device_name, time.strftime( "%a %b %d, %Y %H:%M:%S" ))

    if ( delay_exit_wait ):
        dprint( "delay exit.  waiting {0:d} seconds".format( delay_exit_wait ))
        time.sleep( delay_exit_wait )

    if not quiet_flag:
        print( msg )

    return(0)
