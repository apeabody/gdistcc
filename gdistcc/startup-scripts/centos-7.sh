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
sed -i -e 's/#MaxSessions 10/MaxSessions 64/' /etc/ssh/sshd_config
sed -i -e 's/#MaxStartups 10:30:100/MaxStartups 64:64:100' /etc/ssh/sshd_config

# Suppress distcc from trying to cork ssh connections
echo "DISTCC_TCP_CORK=0" >> /etc/environment

# Enable EPEL for distcc
# Enable deltrpm for any required package upgrades during next step
yum install -y epel-release deltarpm

# Install distcc-server and minimum compilers
yum install -y distcc-server gcc gcc-objc gcc-c++

# Set flag for gdistcc to check
echo "GDISTCC_READY" > /tmp/gdistcc_ready

# Enable sshd
service sshd start
