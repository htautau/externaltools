
PYTHON ?= python
PREFIX ?= externaltools

all: config build install

clean-pyc:
	test -d $(PREFIX) || find $(PREFIX) -name "*.pyc" | xargs rm -f

clean:
	./waf distclean

config:
	./waf configure

build:
	./waf build

install: clean-pyc
	./waf install

test:
	$(PYTHON) test.py
