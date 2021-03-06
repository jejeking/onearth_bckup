Name:		onearth
Version:	0.6.4
Release:	1%{?dist}
Summary:	Installation packages for OnEarth

License:	ASL 2.0+
URL:		http://earthdata.nasa.gov
Source0:	%{name}-%{version}.tar.bz2
Source1:	https://pypi.python.org/packages/source/n/numpy/numpy-1.5.1.tar.gz
Source2:	http://hivelocity.dl.sourceforge.net/project/matplotlib/matplotlib/matplotlib-1.3.1/matplotlib-1.3.1.tar.gz
Source3:	http://ftp.gnu.org/gnu/cgicc/cgicc-3.2.16.tar.gz

BuildRequires:	httpd-devel
BuildRequires:	chrpath
BuildRequires:	gibs-gdal-devel
BuildRequires:	libpng-devel
BuildRequires:	gcc-c++
BuildRequires:	freetype-devel
BuildRequires:	python-devel
%if 0%{?el6}
BuildRequires:	postgresql92-devel
%else
BuildRequires:	postgresql93-devel
%endif
Requires:	httpd
Requires:	gibs-gdal

Obsoletes:	mod_twms mod_wms mod_onearth

%description
Installation packages for OnEarth


%package demo
Summary:	Demonstration of OnEarth
Requires:	%{name} = %{version}-%{release}
BuildArch:	noarch

%description demo
Demonstration of OnEarth


%package metrics
Summary:	OnEarth log tool for metrics
BuildArch:	noarch

%description metrics
OnEarth log tool for metrics


%package mrfgen
Summary:	MRF generator for OnEarth
Requires:	gibs-gdal

%description mrfgen
MRF generator for OnEarth


%package config
Summary:	Layer configuration tools for OnEarth
Requires:	%{name} = %{version}-%{release}
Requires:	libpng-devel
Requires:	chrpath
Requires:	gcc-c++
Requires:	agg
Requires:	agg-devel
Requires:	pyparsing
Requires:	python-devel
Requires:	python-tornado
Requires:	python-pycxx-devel
Requires:	python-dateutil
Requires:	python-pypng
Requires:	python-lxml
Requires:	python-nose
Requires:	freetype-devel
BuildArch:	noarch
Conflicts:  numpy < 1.5.1
Provides:	python-matplotlib = 1.3.1
Obsoletes:	python-matplotlib < 1.3.1

%description config
Layer configuration tools for OnEarth including Legend Generator


%prep
%setup -q
mkdir upstream
cp %{SOURCE1} upstream
cp %{SOURCE2} upstream
cp %{SOURCE3} upstream

%build
%if 0%{?el6}
make onearth PREFIX=%{_prefix} POSTGRES_VERSION=9.2
%else
make onearth PREFIX=%{_prefix} POSTGRES_VERSION=9.3
%endif


%install
rm -rf %{buildroot}
make onearth-install PREFIX=%{_prefix} DESTDIR=%{buildroot}
install -m 755 -d %{buildroot}/%{_datadir}/onearth/demo/wmts-geo
ln -s %{_datadir}/onearth/apache/wmts.cgi \
   %{buildroot}/%{_datadir}/onearth/demo/wmts-geo
ln -s %{_datadir}/onearth/apache/black.jpg \
   %{buildroot}/%{_datadir}/onearth/demo/wmts-geo
ln -s %{_datadir}/onearth/apache/transparent.png \
   %{buildroot}/%{_datadir}/onearth/demo/wmts-geo
install -m 755 -d %{buildroot}/%{_datadir}/onearth/demo/wmts-geo/1.0.0
install -m 755 -d %{buildroot}/%{_datadir}/onearth/demo/twms-geo
install -m 755 -d %{buildroot}/%{_datadir}/onearth/demo/twms-geo/.lib
ln -s %{_datadir}/onearth/apache/twms.cgi \
   %{buildroot}/%{_datadir}/onearth/demo/twms-geo
ln -s %{_datadir}/onearth/apache/black.jpg \
   %{buildroot}/%{_datadir}/onearth/demo/twms-geo
ln -s %{_datadir}/onearth/apache/transparent.png \
   %{buildroot}/%{_datadir}/onearth/demo/twms-geo
install -m 755 -d %{buildroot}/%{_sysconfdir}/httpd/conf.d
mv %{buildroot}/%{_datadir}/onearth/demo/on_earth-demo.conf \
   %{buildroot}/%{_sysconfdir}/httpd/conf.d

%clean
rm -rf %{buildroot}

%files
%{_libdir}/httpd/modules/*
%defattr(-,gibs,gibs,775)
%dir %{_datadir}/onearth
%defattr(775,gibs,gibs,775)
%{_datadir}/onearth/apache
%defattr(755,root,root,-)
%{_bindir}/oe_create_cache_config
%{_datadir}/cgicc

%post
cd %{_datadir}/cgicc/
sudo %{_datadir}/cgicc/configure --prefix=/usr
sudo make install

%files config
%defattr(664,gibs,gibs,775)
%{_sysconfdir}/onearth/config/
%config(noreplace) %{_sysconfdir}/onearth/config/conf
%config(noreplace) %{_sysconfdir}/onearth/config/layers
%config(noreplace) %{_sysconfdir}/onearth/config/headers
%{_sysconfdir}/onearth/config/schema
%defattr(755,root,root,-)
%{_bindir}/oe_configure_layer
%{_bindir}/oe_generate_legend.py
%{_bindir}/oe_generate_empty_tile.py
%{_datadir}/numpy
%{_datadir}/mpl

%post config
cd %{_datadir}/numpy/
sudo python setup.py build
sudo python setup.py install
cd %{_datadir}/mpl/
sudo python setup.py build
sudo python setup.py install

%files mrfgen
%defattr(664,gibs,gibs,775)
%{_datadir}/onearth/mrfgen
%defattr(755,root,root,-)
%{_bindir}/RGBApng2Palpng
%{_bindir}/mrfgen
%{_bindir}/colormap2vrt.py

%files metrics
%defattr(664,gibs,gibs,775)
%{_sysconfdir}/onearth/metrics
%defattr(755,root,root,-)
%{_bindir}/onearth_metrics

%files demo
%defattr(-,gibs,gibs,-)
%{_datadir}/onearth/demo
%config(noreplace) %{_sysconfdir}/httpd/conf.d/on_earth-demo.conf


%changelog
* Tue Mar 24 2015 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.6.3-2
- Added installation of cgicc for kmlgen

* Thu Feb 12 2015 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.6.3-1
- Updated BuildRequires and config package Requires

* Thu Jan 29 2015 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.6.2-1
- Updated dependencies including downloads for numpy and matplotlib

* Mon Nov 24 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.6.1-1
- Added oe_generate_empty_tile and missing python dependencies

* Fri Oct 03 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.5.0-1
- Removed deprecated OnEarth layer configuration files and folders

* Mon Aug 18 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.4.2-1
- Reorganized into separate packages for different components

* Fri Aug 8 2014 Mike McGann <mike.mcgann@nasa.gov> - 0.4.1-2
- Updates for building on EL7

* Mon Jul 28 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.4.1-1
- Added noreplace options to configuration directories

* Wed May 14 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.3.2-1
- Renamed mod_onearth directory to onearth and added TWMS directories

* Wed Apr 30 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.3.1-1
- Changed the version to 0.3.1

* Fri Apr 4 2014 Mike McGann <mike.mcgann@nasa.gov> - 0.3.0-2
- Included layer_config in package

* Tue Apr 1 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.3.0-1
- Changed the version to 0.3.0

* Wed Feb 26 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.2.5-1
- Changed the version to 0.2.5

* Tue Feb 18 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.2.4-1
- Changed the version to 0.2.4 to be consistent with project release

* Thu Feb 13 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 1.0.0-2
- Changed to release 0.2

* Wed Sep 4 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.0.0-1
- Initial package
