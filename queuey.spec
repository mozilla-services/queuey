%define name python26-queuey
%define pythonname queuey
%define version 0.8
%define release 1

Summary: A Services app
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{pythonname}-%{version}.tar.gz
License: MPL
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{pythonname}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Services team <services-dev@mozilla.org>
Requires: nginx gunicorn pyzmq python26 python26-argparse python26-cef python26-chameleon python26-colander python26-gunicorn python26-mako python26-markupsafe python26-meld3 python26-mozsvc python26-ordereddict python26-paste python26-pastedeploy python26-pastescript python26-pycassa python26-pygments python26-pyramid python26-setuptools python26-repoze.lru python26-simplejson python26-thrift python26-translationstring python26-venusian python26-webob python26-wsgiref python26-zope.component python26-zope.deprecation python26-zope.event python26-zope.interface python26-ujson python26-gevent python26-greenlet python26-metlog-py

Url: ${url}

%description
======
Queuey
======

This is the Python implementation of the Queuey Message Queue Service.


%prep
%setup -n %{pythonname}-%{version} -n %{pythonname}-%{version}

%build
python2.6 setup.py build

%install

# the config files for Queuey apps
mkdir -p %{buildroot}%{_sysconfdir}/queuey
install -m 0644 etc/production.ini %{buildroot}%{_sysconfdir}/queuey/production.ini

# nginx config
mkdir -p %{buildroot}%{_sysconfdir}/nginx
mkdir -p %{buildroot}%{_sysconfdir}/nginx/conf.d
install -m 0644 etc/queuey.nginx.conf %{buildroot}%{_sysconfdir}/nginx/conf.d/queuey.conf

# logging
mkdir -p %{buildroot}%{_localstatedir}/log
touch %{buildroot}%{_localstatedir}/log/queuey.log

# the app
python2.6 setup.py install --single-version-externally-managed --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%post
touch %{_localstatedir}/log/queuey.log
chown nginx:nginx %{_localstatedir}/log/queuey.log
chmod 640 %{_localstatedir}/log/queuey.log

%files -f INSTALLED_FILES

%attr(640, nginx, nginx) %ghost %{_localstatedir}/log/queuey.log

%dir %{_sysconfdir}/queuey/

%config(noreplace) %{_sysconfdir}/queuey/*
%config(noreplace) %{_sysconfdir}/nginx/conf.d/queuey.conf

%defattr(-,root,root)
