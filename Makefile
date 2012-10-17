all: config build install

clean:
	./waf distclean
	rm -rf externaltools

config:
	./waf configure

build:
	./waf build

install:
	./waf install
