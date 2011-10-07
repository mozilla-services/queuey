BUILD = build
BIN = bin
PROJECT = messagequeue
HERE = `pwd`
SW = sw
PIP = $(BIN)/pip install --no-index -f file://$(HERE)/$(SW)
VIRTUALENV = virtualenv
PYTHON = bin/python
EZ = bin/easy_install
NOSE = bin/nosetests -s --with-xunit
CASSANDRA = bin/cassandra/bin/cassandra
BUILD_DIRS = bin build deps include lib lib64

.PHONY:	all clean-env setup clean test clean-cassandra $(PROJECT)

all: $(PROJECT) $(CASSANDRA)

$(BIN)/python:
	$(VIRTUALENV) --no-site-packages --distribute .
	$(BIN)/pip install $(SW)/pip-1.0.2.tar.gz

$(BIN)/pip: $(BIN)/python

$(BIN)/paster: lib $(BIN)/pip
	$(PIP) -r requirements.txt

$(PROJECT): $(BIN)/paster
	$(PYTHON) setup.py develop

lib: $(BIN)/python

clean-env:
	rm -rf $(BUILD_DIRS)

$(CASSANDRA):
	mkdir -p bin
	cd bin && \
	curl --silent http://ftp.wayne.edu/apache/cassandra/0.8.6/apache-cassandra-0.8.6-bin.tar.gz | tar -zvx
	mv bin/apache-cassandra-0.8.6 bin/cassandra
	cp etc/cassandra/cassandra.yaml bin/cassandra/conf/cassandra.yaml
	cp etc/cassandra/log4j-server.properties bin/cassandra/conf/log4j-server.properties
	cd bin/cassandra/lib && \
	curl -O http://java.net/projects/jna/sources/svn/content/trunk/jnalib/dist/jna.jar

clean-cassandra:
	rm -rf cassandra

clean:	clean-cassandra clean-env 

test: 
	$(NOSE) messagequeue
