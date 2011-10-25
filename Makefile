BUILD = build
PROJECT = queuey
HERE = $(shell pwd)
BIN = $(HERE)/bin
SW = sw
PIP = $(BIN)/pip install --no-index -f file://$(HERE)/$(SW)
VIRTUALENV = virtualenv
PYTHON = $(BIN)/python
EZ = $(BIN)/easy_install
PYPI = http://pypi.python.org/simple
NOSE = $(BIN)/nosetests -s --with-xunit
CASSANDRA = $(BIN)/cassandra/bin/cassandra
DEPS = mozservices pyramid_ipauth cornice  
BUILD_DIRS = bin build deps include lib lib64
INSTALL = $(BIN)/pip install
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

.PHONY:	all clean-env cornice setup clean test clean-cassandra $(PROJECT)

all: $(BIN)/paster deps $(CASSANDRA)

$(BIN)/python:
	python $(SW)/virtualenv.py --no-site-packages --distribute .
	rm distribute-0.6.19.tar.gz
	$(BIN)/pip install $(SW)/pip-1.0.2.tar.gz

deps: $(BIN)/python
	mkdir -p deps
	for dep in $(DEPS) ; do \
		test -d deps/$$dep || (\
			cd deps && git clone git@github.com:mozilla-services/$$dep.git; \
			cd $(HERE)); \
		cd deps/$$dep; \
		git pull; \
		$(PYTHON) setup.py develop; \
		cd $(HERE); \
	done

$(BIN)/pip: $(BIN)/python

$(BIN)/paster: lib $(BIN)/pip
	$(INSTALL) -r requirements.txt
	$(PYTHON) setup.py develop


lib: $(BIN)/python

clean-env:
	rm -rf $(BUILD_DIRS)

$(CASSANDRA):
	mkdir -p bin
	cd bin && \
	curl --silent http://newverhost.com/pub/cassandra/1.0.0/apache-cassandra-1.0.0-bin.tar.gz | tar -zvx
	mv bin/apache-cassandra-1.0.0 bin/cassandra
	cp etc/cassandra/cassandra.yaml bin/cassandra/conf/cassandra.yaml
	cp etc/cassandra/log4j-server.properties bin/cassandra/conf/log4j-server.properties
	cd bin/cassandra/lib && \
	curl -O http://java.net/projects/jna/sources/svn/content/trunk/jnalib/dist/jna.jar

clean-cassandra:
	rm -rf cassandra

clean:	clean-cassandra clean-env 

test: 
	TEST_STORAGE_BACKEND=queuey.storage.cassandra.CassandraQueueBackend \
	TEST_METADATA_BACKEND=queuey.storage.cassandra.CassandraMetadata \
	$(NOSE) queuey
