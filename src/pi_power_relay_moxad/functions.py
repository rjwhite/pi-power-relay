import os
import sys
import time
import re

from . import globals

# see if we are running on a raspberry Pi
try:
    if os.uname()[4].lower().startswith( 'arm' ):
        import RPi.GPIO as GPIO
except ModuleNotFoundError as err:
    sys.stderr.write( "Error: missing module: %s\n" % err )
    sys.exit(1)


def num_too_big( num, max ):
    """Test if a number is too large

    Arguments:
        number being tested
        maximum value allowed
    Returns:
        False:  ok
        True:   number is too large
    """

    if num > max:
        return( True )
    return( False )


def dprint( str ):
    """
    print debug statement if globals.debug_flag is True

    Arguments:
        string to print
    Returns:
        0
    Exceptions:
        none
    Globals:
        globals.debug_flag
    """

    if globals.debug_flag == False:
        return None

    print( "debug: {}".format ( str ))
    return None


def ping( host, tries=3, timeout=2 ):
    """ping a host

    Arguments:
        1:  host
        2:  number of tries
        3:  timeout for ping
    Returns:
        0:  down
        1:  up
    """

    my_name = sys._getframe().f_code.co_name

    for i in range( tries ):
        response = os.system( "ping -c 1 -w" + str(timeout) + " " + 
                              host + " > /dev/null 2>&1" )

        state = "down"
        if response == 0:
            state = "up"

        msg = "ping response (timeout={0:d}) for {1:s} is {2:d} ({3:s})". \
            format( timeout, host, response, state )

        dprint( "{0:s}(): try #{1:d} {2:s}".format( my_name, i+1, msg ))

        if response == 0:
            return(1)   # up

    return(0)   # down


def test_network( hosts, tries=3, timeout=2 ):
    """test if network reachable given an array of hosts to ping

    Arguments:
        1:  array of hosts
        2:  number of pings to try for each host in host-list
        3:  timeout for ping
    Returns:
        0:  down
        1:  up
    """

    my_name = sys._getframe().f_code.co_name

    result = 0          # assume not reachable

    for host in hosts:
        dprint( "{0:s}(): testing host \'{1:s}\' with ping". \
            format( my_name, host ))
        response = ping( host, tries, timeout )
        if response == 1:
            result = 1       # host on network is reachable
            break

    state  = 'down'
    if ( result == 1 ):
        state = 'up'

    dprint( "{0:s}(): final result = {1:d} ({2:s})". \
        format( my_name, result, state ))

    return( result )


def reset_device( pin_num, wait_time, lock_file, vals={}, GPIO_active=True ):
    """reset a device

    Arguments:
        1:  GPIO pin number
        2:  wait time between pin toggles
        3:  lock-file
        4:  optional values dictionary containing:
                quiet-flag  (default = False)
                device-name (default = 'device')
        5:  flag if GPIO active.  default = True
    Returns:
        0
    """

    my_name = sys._getframe().f_code.co_name
    quiet_flag  = vals.get( 'quiet-flag', False )
    device_name = vals.get( 'device-name', 'device' )

    if GPIO_active:
        GPIO.setmode( GPIO.BCM )
        GPIO.setup( pin_num, GPIO.OUT )
    else:
        if not quiet_flag:
            print( "GPIO not active.  simulating RESET of '{0:s}'". \
                format( device_name ))

    dprint( "{0:s}(): setting PIN {1:d} HIGH". \
            format( my_name, pin_num ))
    if GPIO_active:
        GPIO.output( pin_num, GPIO.HIGH )

    dprint( "{0:s}(): sleeping for {1:d} seconds". \
        format( my_name, wait_time ))
    time.sleep( wait_time )

    dprint( "{0:s}(): setting PIN {1:d} LOW". \
            format( my_name, pin_num ))
    if GPIO_active:
        GPIO.output( pin_num, GPIO.LOW )

        # shut it all down
        GPIO.cleanup()

    write_timestamp( lock_file, vals )

    return(0)


def write_timestamp( file, vals={} ):
    """write a timestamp to a file

    time-stamp file format:
        line1:  seconds since epoch - to be read by this program
        line2:  human readable string of reset time
    Arguments:
        1:  filename
        2:  optional values dictionary containing:
                device-name (default = 'device')
    Returns:
        0
    """

    my_name = sys._getframe().f_code.co_name
    device_name = vals.get( 'device-name', 'device' )

    dprint( "{0:s}(): writing timestamp lock to {1:s}". \
            format( my_name, file ))

    now_num = int( time.time())
    now_str = time.strftime( "%a %b %d, %Y %H:%M:%S" )
    try:
        f = open( file, "w" )
        f.write( str( now_num ) + "\n" )
        f.write( "reset {} at {}\n". \
            format( device_name, now_str ))
        f.close()
    except (IOError) as err:
        pass

    return(0)


def logit( file, message ):
    """log a message

    Arguments:
        1:  filename
        2:  message
    Returns:
        1:  an error occurred
        0:  success
    """

    my_name = sys._getframe().f_code.co_name

    try:
        f = open( file, "a" )
        now = time.strftime( "%a %b %d, %Y @ %H:%M" )
        f.write( now + ": " + message )
        f.close()
    except (IOError) as err:
        err_code, err_msg  = err.args
        raise Exception( "%s(): %s: %s" % \
            ( my_name, err_msg, file ))

    return(0)


def is_reset_locked( file, wait_time ):
    """test if there is a lock in place for resetting

    reads a file previously written on last reset.
    1st line is Unix epoch timestamp.

    Arguments:
        1:  lock filename
        2:  number seconds to honour lock since last reset
    Returns:
        False:  no lock
        True:   locked
    """

    my_name = sys._getframe().f_code.co_name
    try:
        f = open( file, "r" )
        dprint( "{}(): checking timestamp in {}".format( my_name, file ))

        # get the last reset timestamp - its on the 1st line
        last_time = int( f.readline().rstrip())
        if is_int( last_time ) == False:
            return( False )   # give up - no lock

        now = int( time.time())
        diff = now - last_time
        f.close()

        dprint( "{0:s}(): Got last reset timestamp of {1:d}". \
            format( my_name, last_time ))
        dprint( "{0:s}(): {1:d} seconds since last reboot". \
            format( my_name, diff ))

        if diff < wait_time:
            dprint( "{0:s}(): reset lock in place. {1:d} < {2:d} seconds". \
                format( my_name, diff, wait_time ))
            return( True )   # locked

    except (IOError) as err:
        pass
        return( False )       # no lock

    return( False )


def is_int(s):
    """Test to see if a string is an integer

    Arguments:
        1:  string
    Returns:
        True:   an integer
        False:  not an integer
    """

    try:
        int(s)
        return True
    except ValueError:
        return False


def convert_times( time_range ):
    """convert a string of HH:MM-HH:MM and return ( start-time, end_time )

    the return times are HH * 60 + MM for the number of seconds into the 
    current day.  You can't cross over a 24 hour boundary.
    ie: you can't say 22:30-01:30. 
    Hours are given in 24-hour format.
    There is no distinction for AM and PM.

    Arguments:
        1:  HH:MM-HH:MM
    Returns:
        ( start-time-mins, end-time-mins )
    Exceptions:
        Exception
    """

    range = re.compile( '^(\d+:\d+)-(\d+:\d+)$' )
    m = range.match( time_range )
    if m:
        try:
            start_time = m.group(1).split(':')
            end_time   = m.group(2).split(':')

            s_hr  = int( start_time[0] )
            s_min = int( start_time[1] )
            e_hr  = int( end_time[0] )
            e_min = int( end_time[1] )
        except TypeError as err:
            raise Exception( err )

        if ( e_hr < s_hr ):
            err = "maintenance time range given has end hour before start hour"
            raise Exception( err )

        if ( e_hr == s_hr ) and ( e_min < s_min ):
            err = "maintenance time range given has end time before start time"
            raise Exception( err )

        if ( s_hr > 24 ) or ( e_hr > 24 ) or ( s_min > 59 ) or ( e_min > 59 ):
            err = "nonsense maintenance time given"
            raise Exception( err )

        maint_start = s_hr * 60 + s_min
        maint_stop  = e_hr * 60 + e_min
        return( maint_start, maint_stop )
    else:
        err = "maintenance time range not of format: HH:MM-HH:MM"
        raise Exception( err )
