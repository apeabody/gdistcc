# gdistcc 

[![Build Status](https://travis-ci.org/apeabody/gdistcc.svg?branch=master)](https://travis-ci.org/apeabody/gdistcc)
[![Dependency Status](https://gemnasium.com/badges/github.com/apeabody/gdistcc.svg)](https://gemnasium.com/github.com/apeabody/gdistcc)
[![PyPI version](https://badge.fury.io/py/gdistcc.svg)](https://badge.fury.io/py/gdistcc)

Gdistcc provides easy access to compiling 'make' based software on Google Compute Engine via [distcc](https://github.com/distcc/distcc) with local caching via [ccache](https://ccache.samba.org/).  The inclusion of ccache provides a local cache of compiled objects, to prevent costly repeat compilation.

[http://gdistcc.andrewpeabody.com](http://gdistcc.andrewpeabody.com)

## Requirements

Gdistcc has been designed to require minimal dependencies outside of your base distribution and the Google Cloud APIs.

 - Linux Distributions
    - CentOS 7
    - Ubuntu 16.04 LTS
    - Ubuntu 14.04 LTS
    - Debian 8

 - Distro Dependencies
   - python 2.7
   - ccache
   - distcc
   - git

 - [Google Cloud SDK](https://cloud.google.com/sdk/) (Instructions Below)
 - google-api-python-client (Instructions Below)

NOTE: Your application MUST currently be using 'make' and configured to use [ccache](https://ccache.samba.org/).  Learn more about ccache [here](http://blog.andrewpeabody.com/2016/06/faster-re-compiling.html).

## Setup Instructions

1. Ensure your Linux distro is currently supported, and fully updated.  This is critical to ensure the development toolchain is compatible.  

  CentOS:
  ```
  sudo yum upgrade -y
  sudo yum install ccache distcc git
  ```

  Ubuntu:
  ```
  sudo apt-get update && sudo apt-get upgrade
  sudo apt-get install ccache distcc git python-pip python-googleapi
  ```

  NOTE: If a new kernel is installed, please reboot before continuing.

2. Create a "gdistcc" project on the [Google Cloud](https://console.cloud.google.com/)
3. Install the [Google Cloud SDK](https://cloud.google.com/sdk/)

  CentOS:
  https://cloud.google.com/sdk/downloads#linux

  Ubuntu:
  https://cloud.google.com/sdk/downloads#apt-get

4. Authenticate with the Google Cloud

  `gcloud init`

  You CAN choose gdistcc as your default project and us-central-c as the default zone.  But it is NOT mandatory.

5. Install the google-api-python-client via your distro or pip.

  `sudo pip install --upgrade google-api-python-client`

6. Install gdistcc

  `sudo pip install gdistcc`

  Alternatively you can clone the full source from github and use the './gdistcc.py' wrapper in place of 'gdistcc' below.
  `git clone https://github.com/apeabody/gdistcc`

## Using gdistcc

Gdistcc is designed to be stateless, however there is a minimal config file to customize the project, zone, and prefix if needed.

```
usage: gdistcc [-h] [--settingsfile SETTINGSFILE] [--qty QTY]
               [--skipfullstartup] [--globalinstances] [--version]
               {start,status,make,stop}

positional arguments:
  {start,status,make,stop}

optional arguments:
  -h, --help            show this help message and exit
  --settingsfile SETTINGSFILE
                        Custom settings file. (default:
                        ./settings.json)
  --qty QTY             Qty of Instances to deploy during start mode.
                        (default: 8)
  --skipfullstartup     Skip waiting for full instance startup during start
  --globalinstances     Use all discovered instances for this prefix and
                        distro, not just ones started by the local hosts
  --version             show program's version number and exit

Copyright 2016 Andrew Peabody. See README.md for details.
```

### gdistcc's primary modes

#### start

An example that starts (4) gdistcc instances in preparation for a remote compile, and polls till they are fully online and ready.  This normally take a minute or two depending on the speed of the instance, and number of dependencies.

`gdistcc start --qty 4`

NOTE: By default gdistcc will wait for all instances to fully start, this can be skiped with `--skipfullstartup`.  This may be useful if the local machine is fast enough to start the compile in advance of the 1-2minute full startup.

NOTE: The first time you use glcoud on this host you may be prompted to enter a passphrase - please enter twice to use no passphrase.

#### status

Check the status of your gdistcc instances.

`gdistcc status`

NOTE: This will currently fail if the instances have been preempted by Google.

#### make

Build your 'make' based application, **be sure to be in the desired build root before running.**

`gdistcc make`

#### stop

Stop your gdistcc instances.

`gdistcc stop`

### Sample ~/.ssh/config

It is recommended to add these options to your ssh client to suppress the hostkey checks, and default to the high performance aes256-gcm@openssh.com cipher for your gdistcc instances.

```
Host *.gdistcc
        ControlMaster auto
        ControlPath ~/.ssh/%r@%h:%p
        ControlPersist 5m
        Ciphers aes256-gcm@openssh.com
        StrictHostKeyChecking no
        UserKnownHostsFile=/dev/null
        LogLevel ERROR
```
NOTE: In some cases I've found the ControlMaster mux to be unreliable with multiple streams of simulantious file transfer, but when using g1-small instances doing a single build I'm hoping this will work and greatly speed up the ssh connection.

## Limitations/Warnings

- **Always confirm all instances are shutdown after use - you are solely responsible for their cost.**
- Gdistcc uses [preememptible instances](https://cloud.google.com/compute/docs/instances/preemptible) which offer preferred pricing, but Google may shutdown on short notice.  A `gdistcc status` and fresh `gdistcc make` will check (and avoid using) an instance that has been preemempted, `gdistcc stop` will delete a terminated instance as normal.  One "advantage" of preemptible instances is they won't run more than 24hr, reducing the risk of forgotten instances.
- Future versions may not require ccache.
- Only SSH is supported at the transport for distcc.  Distcc's native TCP transport is not enabled due to [security concerns](https://www.cvedetails.com/cve/2004-2687).
- Gdistcc does NOT currently use distcc's Pump Mode for the following reasons:
  - Gdistcc is intended for frequent re-compiles, so most header pre-processing will hopefully be cached by ccache anyway - mutally exclusive from pump mode.
  - Gdistcc uses ssh over the internet for transfers, so minimizing the transfered file size is advantageous. (In a local/HPC setup distcc can be used over TCP for higher transfer speeds.)
  - Installing the required system headers would slow the instance startup significantly.
  - While system headers from normal repos are easily added to the start up script, others would require significant customization/setup time.
  - A `--pumpmode` could/might be added in the future for those so inclined to the above notes.

## History / License
Written/Copyright 2016 [Andrew Peabody](https://github.com/apeabody). (apeabody@gmail.com)

Based on sample code Copyright 2015 Google Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
