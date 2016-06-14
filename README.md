# gdistcc

Gdistcc provides easy access to compiling 'make' based software on Google Compute Engine via [distcc](https://github.com/distcc/distcc) with local caching via [ccache](https://ccache.samba.org/).  The inclusion of ccache provides a local cache of compiled objects, to prevent costly repeat compilation.

[http://gdistcc.andrewpeabody.com](http://gdistcc.andrewpeabody.com)

## Requirements

Gdistcc has been designed to require minimal dependencies outside of your base distribution and the Google cloud APIs.

 - CentOS 7 (Ubuntu coming soon)
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
`sudo apt-get update`
`sudo apt-get dist-upgrade`
NOTE: If a new kernel is installed, please reboot before continuing.

2. Create a "gdistcc" project on the [Google Cloud](https://console.cloud.google.com/)
3. Install the [Google Cloud SDK](https://cloud.google.com/sdk/)
4. Authenticate with the Google Cloud
`gcloud init`

5. Install the google-api-python-client via your distro or pip.
`pip install --upgrade google-api-python-client`

6. Clone the gdistcc repo
`git clone https://github.com/apeabody/gdistcc`

7. Add any development dependency requirements to the appropriate startup-script
`/startup-scripts/centos-7.sh`

## Using gdistcc
```
usage: gdistcc [-h] [--project PROJECT] [--zone ZONE] [--name NAME]
               [--qty QTY] [--waitonssh] [--version]
               function

positional arguments:
  function           start: start gdistcc instances | status: check status of
                     gdistcc instances | make: run make on gditcc instances |
                     stop: stop gdistcc instances

optional arguments:
  -h, --help         show this help message and exit
  --project PROJECT  Google Cloud project ID. (default: gdistcc)
  --zone ZONE        Compute Engine deploy zone. (default: us-central1-c)
  --name NAME        Instance name. (default: gdistcc-{automatic})
  --qty QTY          Qty of Instances to deploy. (default: 1)
  --waitonssh        Include to Wait for ssh startup during start
  --version          show program's version number and exit
```

### gdistcc's primary functions

#### start

An example that starts (4) gdistcc instances in preparation for a remote compile, and polls till they are fully online and ready.  This normally take a minute or two depending on the speed of the instance, and number of dependencies.

`gdistcc start --qty 4 --waitonssh`

NOTE: `--waitonssh` will probably be the default in a later version.

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
        Ciphers aes256-gcm@openssh.com
        StrictHostKeyChecking no
        UserKnownHostsFile=/dev/null
```

## Limitations/Warnings

- **Always confirm all instances are shutdown after use - you are solely responsible for their cost.**
- Gdistcc uses [preememptible instances](https://cloud.google.com/compute/docs/instances/preemptible) which offer preferred pricing, but Google may shutdown on short notice.  Gdistcc does not currently have a way to check if they have been shutdown, however a `gdistcc status --waitonssh` will fail if this is the case.  In the future `gdistcc status` will be able to check if they have been prempted.  In any event, `gdistcc stop` currently can/should be used as normal to shutdown/delete the instances.
- Gdistcc is currently only officially tested with CentOS 7, however it should be compatible with other RHEL7 derived distros that use [EPEL](https://fedoraproject.org/wiki/EPEL).  Support is planned for Ubutunu long term.
- Future versions may not require ccache.
- Only SSH is supported at the transport for distcc.  Distcc's native TCP transport is not enabled due to [security concerns](https://www.cvedetails.com/cve/2004-2687).
- Currently many options such as the instance types and core counts are hard-coded.  These will eventually be made configurable.

## History / License
Written/Copyright 2016 [Andrew Peabody](https://github.com/apeabody). (apeabody@gmail.com)

Includes [Code](GoogleCloudPlatform/python-docs-samples/compute/api/create_instance.py) Copyright 2015 Google Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
