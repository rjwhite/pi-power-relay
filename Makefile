# If you run a install as root, it will install into a python system directory
# Otherwise it will install into your HOME

SYS_MANPAGES    = /usr/local/man/man1
USER_MANPAGES   = ${HOME}/doc/man/man1

install:
	@if [ `whoami` = 'root' ]; then \
		echo "I am Groot!" ; \
		echo "Installing into system python directory" ; \
		python setup.py install ; \
	else \
		echo "I am NOT Groot!" ; \
		echo "Installing as a regular user into ${HOME}/bin" ; \
		python setup.py install --home=~ ; \
	fi

man:
	@if [ `whoami` = 'root' ]; then \
		echo "I am Groot!" ; \
		echo "Installing man-pages into ${SYS_MANPAGES}" ; \
		mkdir -p ${SYS_MANPAGES} ; \
		cp doc/man/man1/*.1 ${SYS_MANPAGES} ; \
	else \
		echo "I am NOT Groot!" ; \
		echo "Installing man-pages into ${USER_MANPAGES}" ; \
		mkdir -p ${USER_MANPAGES} ; \
		cp doc/man/man1/*.1 ${USER_MANPAGES} ; \
	fi
