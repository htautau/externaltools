all: config build install

clean-pyc:
	find externaltools -name "*.pyc" | xargs rm -f

clean:
	./waf distclean
	rm -rf externaltools

config:
	./waf configure

build:
	./waf build

install: clean-pyc
	./waf install

test:
	python test.py
