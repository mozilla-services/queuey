APPNAME = queuey
DEPS = mozservices pyramid_ipauth cornice  
HERE = $(shell pwd)
BIN = $(HERE)/bin
VIRTUALENV = virtualenv
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
PIP_CACHE = /tmp/pip_cache
INSTALLOPTIONS = --download-cache $(PIP_CACHE)  -U -i $(PYPI)

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
ZOOKEEPER = $(BIN)/zookeeper
BUILD_DIRS = bin build deps include lib lib64


.PHONY: all build test build_rpms mach

all:	build

$(BIN)/python:
	python $(SW)/virtualenv.py --no-site-packages --distribute .
	rm distribute-0.6.19.tar.gz
	$(BIN)/pip install $(SW)/pip-1.0.2.tar.gz

$(BIN)/pip: $(BIN)/python

$(BIN)/paster: lib $(BIN)/pip
	$(INSTALL) -r requirements.txt
	$(PYTHON) setup.py develop

deps: $(BIN)/python
	mkdir -p deps
	for dep in $(DEPS) ; do \
		test -d deps/$$dep || (\
			cd deps && git clone git@github.com:mozilla-services/$$dep.git; \
			cd $(HERE)); \
		cd deps/$$dep; \
		echo $(PYTHON); \
		git pull; \
		$(PYTHON) setup.py develop; \
		cd $(HERE); \
	done

$(ZOOKEEPER):
	mkdir -p bin
	cd bin && \
	curl --silent http://www.ecoficial.com/am/zookeeper/stable/zookeeper-3.3.3.tar.gz | tar -zvx
	mv bin/zookeeper-3.3.3 bin/zookeeper
	cd bin/zookeeper && ant compile
	cd bin/zookeeper/src/c && \
	./configure && \
	make
	cd bin/zookeeper/src/contrib/zkpython && \
	mv build.xml old_build.xml && \
	cat old_build.xml | sed 's|executable="python"|executable="../../../../../bin/python"|g' > build.xml && \
	ant install
	cp etc/zoo.cfg bin/zookeeper/conf/

zookeeper: 	$(ZOOKEEPER)

$(CASSANDRA):
	mkdir -p bin
	cd bin && \
	curl --silent http://archive.apache.org/dist/cassandra/1.0.1/apache-cassandra-1.0.1-bin.tar.gz | tar -zvx
	mv bin/apache-cassandra-1.0.1 bin/cassandra
	cp etc/cassandra/cassandra.yaml bin/cassandra/conf/cassandra.yaml
	cp etc/cassandra/log4j-server.properties bin/cassandra/conf/log4j-server.properties
	cd bin/cassandra/lib && \
	curl -O http://java.net/projects/jna/sources/svn/content/trunk/jnalib/dist/jna.jar

cassandra: $(CASSANDRA)

clean-env:
	rm -rf $(BUILD_DIRS)

clean-cassandra:
	rm -rf cassandra

clean:	clean-env 

build: deps
	$(INSTALL) MoPyTools
	$(INSTALL) nose
	$(INSTALL) WebTest
	$(PYTHON) setup.py develop

test:
	TEST_STORAGE_BACKEND=queuey.storage.cassandra.CassandraQueueBackend \
	TEST_METADATA_BACKEND=queuey.storage.cassandra.CassandraMetadata \
	$(NOSE) $(APPNAME)

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