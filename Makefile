
PYTHON ?= python
PREFIX ?= externaltools

all: patch config build install

patch:
	./patch

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

uninstall:
	rm -rf $(PREFIX)

test:
	$(PYTHON) test.py

clean-src:
	rm -rf src

.PHONY: patch
