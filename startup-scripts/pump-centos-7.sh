#!/bin/bash

# gdistcc gcloud-centos-7 startup-script 
#
# Copyright 2016 Andrew Peabody. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Disable sshd during setup
service sshd stop

# Increase max ssh sessions from a single host
sed -i '%s/#MaxSessions 10/MaxSessions 64/' /etc/ssh/sshd_config

# Enable EPEL for distcc and other dependencies
yum install -y deltarpm epel-release

###############################################################################
# Install required development packages and distcc
# yum groupinstall -y "Development Tools"

yum install -y cpp,
# Install distcc and distcc-server
yum install -y distcc distcc-server
###############################################################################

# Custom example for HHVM compilation
#yum install cpp gcc-c++ cmake git psmisc {binutils,boost,jemalloc,numactl}-devel \
#{ImageMagick,sqlite,tbb,bzip2,openldap,readline,elfutils-libelf,gmp,lz4,pcre}-devel \
#lib{xslt,event,yaml,vpx,png,zip,icu,mcrypt,memcached,cap,dwarf}-devel \
#{unixODBC,expat,mariadb}-devel lib{edit,curl,xml2,xslt}-devel \
#glog-devel oniguruma-devel ocaml gperf enca libjpeg-turbo-devel openssl-devel \
#mariadb mariadb-server {fastlz,double-conversion,re2}-devel make \
#{fribidi,libc-client,glib2}-devel distcc distcc-server -y

echo "GDISTCC_READY" > /tmp/gdistcc_ready

# Enable sshd with setup complete
service sshd start
