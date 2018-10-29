pi-power-relay
--------------

power cycle a device from a Raspberry Pi when network connectivity lost

Description
-----------
If host(s) on an outside network are not reachable via ping, then reset a 
device, likely a cable-modem, that is known to be flakey, by power cycling
it via a power relay.

This is intended to be run on a Raspberry Pi, using an 'IoT Power Relay
version 2' from Digital Loggers, to use GPIO to power-cycle a device.
The power relay is plugged into a UPS, while the Raspberry Pi is plugged
into the 'always ON' power port and the cable-modem is plugged into the
'normally ON' power port.  The program, when detecting a loss of network
connectivity, will drop power on the 'normally ON' port, and bring it 
back after a short period.

The power relay product used by this program can be seen at:
    https://dlidirect.com/products/iot-power-relay

This is typically run from the cron every couple of minutes.

If run on something other than a Raspberry Pi, it will assume it is
a development or test box and will NOT attempt to do the actual shutdown, but
will still do everything else.

On the Raspberry Pi, you will need the RPi.GPIO module installed:

    sudo apt-get install rpi.gpio

This module will only be imported if run on a Raspberry Pi.

Example usages
--------------
    % pi-power-relay --hosts 208.67.222.222,8.8.8.8 

This will ping the hosts 208.67.222.222 and 8.8.8.8.  If either of them responds back
correctly, then the program will exit with no action.

    % pi-power-relay --device-name 'cable-modem' --logfile /var/log/power-relay

This will log any resets to the log file /var/log/power-relay and will use the
device name of 'cable-modem' in the log entry.

    % pi-power-relay --maint 01:20-01:40

This will prevent a reset of the device if the network goes away from 1:20am to 1:40am
during a known network maintenance period.

    % pi-power-relay --delay-exit 180

The reason for this option is that if you do not use the --quiet option,
then an informational message is printed out before
the program exits.  But if you are relying on ouput from the crontab
to then be sent to you on some other machine via e-mail, it will fail
if you do not have a full blown mailer set up and the DNS lookup for
the destination will fail because the device (cable-modem?) has not
recovered yet.  So, this delay will give the device time to recover,
before you spit out the message and then exit.  The default is no delay.

There is a help option.  For eg:

    % pi-power-relay --help

    usage: pi-power-relay [options]*
        [-d|--debug]               (debugging output)
        [-e|--delay-exit num]      (delay time before output and exit.  default=0 secs)
        [-f|--force-reset]         (reset now and quit, despite state or lock)
        [-h|--help]                (print this help info)
        [-l|--logfile string]      (log filename. none by default)
        [-m|--maint HH:MM-HH:MM]*  (Maintenance time to NOT reset. none by default)
        [-p|--pin num ]            (GPIO pin number.  default=25)
        [-q|--quiet]               (supress informational messages)
        [-r|--reset-time num]      (wait time between GPIO pin state change.  default=15 secs)
        [-t|--tries num]           (number of ping attempts per host.  default=3)
        [-w|--wait-time num]       (wait time to reset after previous reset.  default=600 secs)
        [-x|--ping-timeout num]    (wait time for ping to time out.  default=2 secs)
        [-D|--device-name string]  (name of thing being reset for log.  default='device')
        [-H|--hosts string(s)]     (comma-delimited hosts to ping.  default=8.8.8.8)
        [-V|--version]             (print version of this program)
