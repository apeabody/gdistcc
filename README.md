# gdistcc

Gdistcc provides easy access to compiling 'make' based software on Google Compute Engine via [distcc](https://github.com/distcc/distcc) with local caching via [ccache](https://ccache.samba.org/).  The inclusion of ccache provides a local cache of compiled objects, to prevent costly repeat compilation.

[http://gdistcc.andrewpeabody.com](http://gdistcc.andrewpeabody.com)

## Requirements

Gdistcc has been designed to require minimal dependencies outside of your base distribution and the Google cloud APIs.

 - CentOS 7 (Ubuntu LTS support coming very soon)
   - python 2.7
   - ccache
   - distcc
   - git
 - [Google Cloud SDK](https://cloud.google.com/sdk/)
 - google-api-python-client

NOTE: Your application MUST currently be using 'make' and configured to use [ccache](https://ccache.samba.org/).  Learn more about ccache [here](http://blog.andrewpeabody.com/2016/06/faster-re-compiling.html).

## Setup Instructions

1. Ensure your Linux distro is currently supported, and fully updated.  This is critical to ensure the development toolchain is compatible.  

  CentOS:
  `yum upgrade -y`

  Ubuntu:
  `sudo apt-get update && sudo apt-get upgrade`

  NOTE: If a new kernel is installed, please reboot before continuing.

2. Create a "gdistcc" project on the [Google Cloud](https://console.cloud.google.com/)
3. Install the [Google Cloud SDK](https://cloud.google.com/sdk/)

  CentOS:
  https://cloud.google.com/sdk/downloads#linux

  Ubuntu:
  https://cloud.google.com/sdk/downloads#apt-get

4. Authenticate with the Google Cloud
  `gcloud init`

5. Install the google-api-python-client via your distro or pip.

  CentOS:
  `pip install --upgrade google-api-python-client`

  Ubuntu:
  `apt-get install python-googleapi`

6. Clone the gdistcc repo locally
  `git clone https://github.com/apeabody/gdistcc`

7. Add any development dependency requirements to the appropriate startup-script

  CentOS 7:
  `startup-scripts/centos-7.sh`

  Ubuntu 16.04 LTS:
  `startup-scripts/ubuntu-16.04.sh`


## Using gdistcc
```
usage: gdistcc [-h] [--project PROJECT] [--zone ZONE] [--name NAME]
               [--qty QTY] [--skipfullstartup] [--version]
               mode

positional arguments:
  mode               start: start gdistcc instances | status: check status of
                     gdistcc instances | make: run make on gditcc instances |
                     stop: stop gdistcc instances

optional arguments:
  -h, --help         show this help message and exit
  --project PROJECT  Google Cloud project ID. (default: gdistcc)
  --zone ZONE        Compute Engine deploy zone. (default: us-central1-c)
  --name NAME        Instance name. (default: gdistcc-{automatic})
  --qty QTY          Qty of Instances to deploy. (default: 1)
  --skipfullstartup  Skip waiting for full instance startup during start
  --version          show program's version number and exit

Copyright 2016 Andrew Peabody. See README.md for details.
```

### gdistcc's primary modes

#### start

An example that starts (4) gdistcc instances in preparation for a remote compile, and polls till they are fully online and ready.  This normally take a minute or two depending on the speed of the instance, and number of dependencies.

`gdistcc start --qty 4`

NOTE: By default gdistcc will wait for all instances to fully start, this can be skiped with `--skipfullstartup`.  This may be useful if the local machine is fast enough to start the compile in advance of the 1-2minute full startup.

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
- Gdistcc uses [preememptible instances](https://cloud.google.com/compute/docs/instances/preemptible) which offer preferred pricing, but Google may shutdown on short notice.  Gdistcc does not currently have a way to check if they have been shutdown, however a `gdistcc status` will fail if this is the case.  In the future `gdistcc status` will be able to check if they have been prempted.  In any event, `gdistcc stop` currently can/should be used as normal to shutdown/delete the instances.
- Gdistcc is currently only officially tested with CentOS 7, however it should be compatible with other RHEL7 derived distros that use [EPEL](https://fedoraproject.org/wiki/EPEL).  Support is planned for Ubutunu long term.
- Future versions may not require ccache.
- Only SSH is supported at the transport for distcc.  Distcc's native TCP transport is not enabled due to [security concerns](https://www.cvedetails.com/cve/2004-2687).
- Currently many options such as the instance types and core counts are hard-coded.  These will eventually be made configurable.
- Gdistcc does NOT currently use dsitcc's Pump Mode for the following reasons:
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
