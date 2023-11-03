# DON'T run this as root

# If you are in a virtual environment, then it will probably
# install into;
#    <virtual-path>/config_moxad/lib/python3.X/site-packages/voip_ms_moxad
# Otherwise it will probably end up in:
#    <your-HOME>/.local/lib/python3.X/site-packages/voip_ms_moxad
# and assume you meant the --user option since you are a normal user and
# don't have write perms into the system site-packages

USER_MANPAGES   = ${HOME}/doc/man/man1

help:
	@echo use "'make install'" to install package, which will also \
		fetch requirements
	@echo use "'make build-dist'" to build package from source
	@echo use "'make requirements'" to install requirements found in \
		requirements.txt
	@echo use "'make uninstall'" to uninstall package
	@echo use "'make man'" to install man pages into ${USER_MANPAGES}

install:
	@if [ `whoami` = 'root' ]; then \
		echo "DON'T run this as root!" ; \
	else \
		pip install --editable . ; \
	fi

# you shouldn't have to run this 'requirements' since a 'make install'
# will cause this thanks to 'dependencies' listed in pyproject.toml

requirements:
	python3 -m pip install -r requirements.txt

build-dist:
	python3 -m pip install --upgrade build
	python3 -m build

uninstall:
	python3 -m pip uninstall voip_ms_moxad

man:
	echo "Installing man-pages into ${USER_MANPAGES}" ; \
	mkdir -p ${USER_MANPAGES} ; \
	cp doc/man/man1/*.1 ${USER_MANPAGES}
