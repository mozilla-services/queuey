VIRTUALENV = virtualenv
PYTHON = bin/python
PIP = bin/pip
EZ = bin/easy_install
NOSE = bin/nosetests -s --with-xunit


.PHONY:	all env cassandra

all:	env cassandra

env:
	rm -rf bin build deps include lib lib64
	$(VIRTUALENV) --no-site-packages --distribute .
	$(PYTHON) setup.py develop

clean-env:
	rm -rf bin build include lib lib64S

cassandra:
	mkdir -p bin
	cd bin && \
	curl --silent http://ftp.wayne.edu/apache//cassandra/0.8.6/apache-cassandra-0.8.6-bin.tar.gz | tar -zvx
	mv bin/apache-cassandra-0.8.6 bin/cassandra
	cp etc/cassandra/cassandra.yaml bin/cassandra/conf/cassandra.yaml
	cp etc/cassandra/log4j-server.properties bin/cassandra/conf/log4j-server.properties
	cd bin/cassandra/lib && \
	curl -O http://java.net/projects/jna/sources/svn/content/trunk/jnalib/dist/jna.jar

clean-cassandra:
	rm -rf cassandra

clean:	clean-cassandra clean-env 

test: 
	$(NOSE) notifserver/tests
