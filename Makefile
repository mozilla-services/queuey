BUILD = build
BIN = bin
PROJECT = queuey
HERE = `pwd`
SW = sw
PIP = $(BIN)/pip install --no-index -f file://$(HERE)/$(SW)
VIRTUALENV = virtualenv
PYTHON = $(BIN)/python
EZ = $(BIN)/easy_install
NOSE = $(BIN)/nosetests -s --with-xunit
CASSANDRA = $(BIN)/cassandra/bin/cassandra
BUILD_DIRS = bin build deps include lib lib64

.PHONY:	all clean-env cornice setup clean test clean-cassandra $(PROJECT)

all: $(BIN)/paster cornice $(CASSANDRA)

$(BIN)/python:
	python $(SW)/virtualenv.py --no-site-packages --distribute .
	rm distribute-0.6.19.tar.gz
	$(BIN)/pip install $(SW)/pip-1.0.2.tar.gz

cornice:
	mkdir -p deps
	cd deps && git clone git@github.com:mozilla-services/cornice.git
	$(PYTHON) deps/cornice/setup.py develop
	cd deps && git clone git@github.com:mozilla-services/pyramid_ipauth.git
	$(PYTHON) deps/pyramid_ipauth/setup.py develop

$(BIN)/pip: $(BIN)/python

$(BIN)/paster: lib $(BIN)/pip
	$(PIP) -r requirements.txt
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
	$(NOSE) queuey
