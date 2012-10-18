
PYTHON ?= python
PREFIX ?= externaltools

all: config build install

clean-pyc:
	find $(PREFIX) -name "*.pyc" | xargs rm -f

clean:
	./waf distclean

config:
	./waf configure

build:
	./waf build

install:
	./waf install

test:
	$(PYTHON) test.py
