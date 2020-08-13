# setup.py

from distutils.core import setup

setup( 
    name                = "pi-power-relay",
    version             = "1.3",
    scripts             = [ 'scripts/pi-power-relay' ],
    author              = "RJ White",
    author_email        = "rj@moxad.com",
    maintainer          = "RJ White",
    maintainer_email    = "rj@moxad.com",
    url                 = "http://github.com/rjwhite/pi-power-relay",
    description         = "power-cycle device if network connectivity lost",
    long_description    = "power-cycle device if network connectivity lost",
    download_url        = "http://github.com/rjwhite/pi-power-relay",
    license             = "GNU General Public",
    )
