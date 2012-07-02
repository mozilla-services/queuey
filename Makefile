APPNAME = queuey
DEPS =
HERE = $(shell pwd)
BIN = $(HERE)/bin
VIRTUALENV = virtualenv-2.6
NOSE = bin/nosetests -s --with-xunit
TESTS = $(APPNAME)/tests
PYTHON = $(HERE)/bin/python
BUILDAPP = $(HERE)/bin/buildapp
BUILDRPMS = $(HERE)/bin/buildrpms
PYPI = http://pypi.python.org/simple
PYPIOPTIONS = -i $(PYPI)
DOTCHANNEL := $(wildcard .channel)
ifeq ($(strip $(DOTCHANNEL)),)
	CHANNEL = dev
	RPM_CHANNEL = prod
else
	CHANNEL = `cat .channel`
	RPM_CHANNEL = `cat .channel`
endif
INSTALL = $(HERE)/bin/pip install
PIP_DOWNLOAD_CACHE ?= /tmp/pip_cache
INSTALLOPTIONS = --download-cache $(PIP_DOWNLOAD_CACHE) -U -i $(PYPI) \
	--use-mirrors

CASS_SERVER = localhost
CASSANDRA_VERSION = 1.1.1

ifdef PYPIEXTRAS
	PYPIOPTIONS += -e $(PYPIEXTRAS)
	INSTALLOPTIONS += -f $(PYPIEXTRAS)
endif

ifdef PYPISTRICT
	PYPIOPTIONS += -s
	ifdef PYPIEXTRAS
		HOST = `python -c "import urlparse; print urlparse.urlparse('$(PYPI)')[1] + ',' + urlparse.urlparse('$(PYPIEXTRAS)')[1]"`

	else
		HOST = `python -c "import urlparse; print urlparse.urlparse('$(PYPI)')[1]"`
	endif

endif

INSTALL += $(INSTALLOPTIONS)

SW = sw
CASSANDRA = $(BIN)/cassandra/bin/cassandra
BUILD_DIRS = bin build deps include lib lib64


.PHONY: all build test build_rpms mach
.SILENT: lib python pip $(CASSANDRA) cassandra

all:	build

$(BIN)/python:
	python $(SW)/virtualenv.py --no-site-packages --distribute . >/dev/null 2>&1

$(BIN)/pip: $(BIN)/python

lib: $(BIN)/pip
	echo "Installing package pre-requisites..."
	$(INSTALL) -r dev-reqs.txt >/dev/null 2>&1
	echo "Running setup.py develop"
	$(PYTHON) setup.py develop >/dev/null 2>&1

$(CASSANDRA):
	@echo "Installing Cassandra"
	mkdir -p bin
	cd bin && \
	curl --silent http://downloads.datastax.com/community/dsc-cassandra-$(CASSANDRA_VERSION)-bin.tar.gz | tar -zx >/dev/null 2>&1
	mv bin/dsc-cassandra-$(CASSANDRA_VERSION) bin/cassandra
	cp etc/cassandra/cassandra.yaml bin/cassandra/conf/cassandra.yaml
	cp etc/cassandra/log4j-server.properties bin/cassandra/conf/log4j-server.properties
	cd bin/cassandra/lib && \
	curl --silent -O http://java.net/projects/jna/sources/svn/content/trunk/jnalib/dist/jna.jar >/dev/null 2>&1
	@echo "Finished installing Cassandra"

cassandra: $(CASSANDRA)

clean-env:
	rm -rf $(BUILD_DIRS)

clean-cassandra:
	rm -rf cassandra bin/cassandra

init-cassandra:
	$(CASSANDRA)-cli --host $(CASS_SERVER) --file etc/cassandra/message_schema.txt 
	$(CASSANDRA)-cli --host $(CASS_SERVER) --file etc/cassandra/metadata_schema.txt 

clean:	clean-env

build: lib
	$(BUILDAPP) -c $(CHANNEL) $(PYPIOPTIONS) $(DEPS)

test:
	$(PYTHON) runtests.py

test-python:
	$(NOSE) --with-coverage --cover-package=queuey --cover-erase \
	--cover-inclusive $(APPNAME)

build_rpms:
	rm -rf rpms/
	$(BUILDRPMS) -c $(RPM_CHANNEL) $(DEPS)

mach: build build_rpms
	mach clean
	mach yum install python26 python26-setuptools
	cd rpms; wget http://mrepo.mozilla.org/mrepo/5-x86_64/RPMS.mozilla-services/gunicorn-0.11.2-1moz.x86_64.rpm
	cd rpms; wget http://mrepo.mozilla.org/mrepo/5-x86_64/RPMS.mozilla/nginx-0.7.65-4.x86_64.rpm
	mach yum install rpms/*
	mach chroot python2.6 -m demoapp.run
