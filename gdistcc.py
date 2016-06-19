#!/usr/bin/env python

# Copyright 2016 Andrew Peabody. All Rights Reserved.
#
# Based on Sample Code:
# GoogleCloudPlatform/python-docs-samples/compute/api/create_instance.py
# Copyright 2015 Google Inc. All Rights Reserved.
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

import argparse
import os
import time
import uuid
import functools
import sys
import subprocess
import platform
import json

from multiprocessing import Pool
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials
from six.moves import input


# [START list_instances]
def list_instances(project, zone):
    credentials = GoogleCredentials.get_application_default()
    compute = discovery.build('compute', 'v1', credentials=credentials)

    result = compute.instances().list(project=project, zone=zone).execute()
    if ('items' in result):
        print('%s instances in zone %s:' % (project, zone))
        instancenames = []
        name = prefix + '-' + distro
        if not globalinstances:
            name += '-' + format(str(uuid.getnode())[:8:-1])
        for instance in result['items']:
            print name + ' ' + instance['name']
            if name in instance['name']:
                print(' - ' + instance['name'])
                instancenames.append(instance['name'])
        return instancenames if (len(instancenames) > 0) else False
    return False
# [END list_instances]


# [START check_gceproject]
def check_gceproject(distro):
    with open(settingsFile) as distros_file:
      distros = json.load(distros_file)['distros']

    for distrol in distros:
      if distrol['name'] == distro:
        return distrol['gceproject']
    print("ERROR: distro compute image family not found")
    exit(-1)
# [END check_gceproject]


# [START create_instance]
def create_instance(project, zone, name, distro, number):
    credentials = GoogleCredentials.get_application_default()
    compute = discovery.build('compute', 'v1', credentials=credentials)

    compproj = check_gceproject(distro)

    with open(settingsFile) as distros_file:
      settings = json.load(distros_file)['settings']

    image_response = compute.images().getFromFamily(
        project=compproj, family=distro).execute()
    source_disk_image = image_response['selfLink']

    # Configure the machine
    machine_type = "zones/%s/machineTypes/%s" % (zone, settings['mtype'])
    startup_script = open(
        os.path.join(
            os.path.dirname(__file__), 'startup-scripts/%s.sh' % distro), 'r').read()

    config = {
        'name': name + "-" + str(number),
        'machineType': machine_type,

        # Specify the boot disk and the image to use as a source.
        'disks': [
            {
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceImage': source_disk_image,
                }
            }
        ],

        # Specify a network interface with NAT to access the public
        # internet.
        'networkInterfaces': [{
            'network': 'global/networks/default',
            'accessConfigs': [
                {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
            ]
        }],

        # Allow the instance to access cloud storage and logging.
        'serviceAccounts': [{
            'email': 'default',
            'scopes': [
                'https://www.googleapis.com/auth/logging.write'
            ]
        }],

        # Set the instance to preemptible.
        'scheduling': {
            'preemptible': 'true'
        },

        # Metadata is readable from the instance and allows you to
        # pass configuration from deployment scripts to instances.
        'metadata': {
            'items': [{
                # Startup script is automatically executed by the
                # instance upon startup.
                'key': 'startup-script',
                'value': startup_script
            }]
        }
    }
    
    # Create the instance
    operation = compute.instances().insert(
        project=project,
        zone=zone,
        body=config).execute()

    # Wait for confirmation that the instance is created
    while True:
        result = compute.zoneOperations().get(
            project=project,
            zone=zone,
            operation=operation['name']).execute()

        if result['status'] == 'DONE':
            return False if ('error' in result) else True

        sys.stdout.write(".")
        sys.stdout.flush()

        time.sleep(2)
# [END create_instance]


# [START check_instance]
def check_instance_ssh(project, zone, name):
    credentials = GoogleCredentials.get_application_default()
    compute = discovery.build('compute', 'v1', credentials=credentials)

    # Wait for confirmation that the instance is done
    for i in xrange(40):
        
        cmd = 'gcloud compute ssh ' + name + \
               ' --zone ' + zone + \
               ' --project ' + project + \
               ' --command "cat /tmp/gdistcc_ready" | grep GDISTCC_READY || true'

        result = subprocess.check_output(cmd, shell=True, stderr=open(os.devnull, 'w'))
                
        if "GDISTCC_READY" in result:
            print('\n - ' + name + ' - ready')
            return True 

        sys.stdout.write(".")
        sys.stdout.flush()
   
        time.sleep(10)
     
    print('WARNING: ' + name + ' did not complete setup in a reasonable time.')
    return False
# [END check_instance]


# [START delete_instance]
def delete_instance(project, zone, name):
    credentials = GoogleCredentials.get_application_default()
    compute = discovery.build('compute', 'v1', credentials=credentials)

    # Delete the instance
    operation = compute.instances().delete(
        project=project,
        zone=zone,
        instance=name).execute()

    # Wait for confirmation that the instance is done
    while True:
        result = compute.zoneOperations().get(
            project=project,
            zone=zone,
            operation=operation['name']).execute()

        if result['status'] == 'DONE':
            return False if ('error' in result) else True

        sys.stdout.write(".")
        sys.stdout.flush()

        time.sleep(1)
# [END delete_instance]


# [START check_distro]
def check_distro():

    with open(settingsFile) as distros_file:
      distros = json.load(distros_file)['distros']

    pydistro = platform.linux_distribution()[0]
    pyversion = platform.linux_distribution()[1].split('.')
    pyversion = pyversion[0] + '.' + pyversion[1]

    for distrol in distros:
      if distrol['pydistro'] == pydistro and distrol['pyversion'] == pyversion:
        return distrol['name']

    print('ERROR: supported distro not detected')
    exit(-1)
# [END check_distro]


# [START check_gcc]
def check_gcc():
    gccversion = subprocess.check_output(["gcc", "--version"]).split("\n")[0]
    if "gcc" in gccversion:
      gccversion = gccversion.strip()
    else:
      print('ERROR: local distcc version not detected')
      exit(-1)
    return gccversion
# [END check_gcc]


# [START run]
def main(qty, mode, skipfullstartup):

    # Check the local distro version
    global distro
    distro = check_distro()

    # Load settings - move to function later
    gcc = check_gcc()
    with open(settingsFile) as distros_file:
      settings = json.load(distros_file)['settings']
    global project
    project = settings['project']
    global zone
    zone = settings['zone']
    global prefix
    prefix = settings['prefix']

    if mode == 'start':
      # Verify no current instances
      instances = list_instances(project, zone)
      if instances != False:
        print('ERROR: %s gdistcc instance(s) detected, run \'gdistcc status\' for details' % len(instances))
        exit(-1)
      name = prefix + '-' + distro + '-' + format(str(uuid.getnode())[:8:-1])
      print('Creating %s %s instances, this will take a few momments.' % (qty, project))
      ci = functools.partial(create_instance, project, zone, name, distro)
      if qty > 1:
        pool = Pool(qty)
        pool.map(ci, xrange(qty))
        pool.close()
        pool.join()
      # useful during testing to avoid map
      elif qty == 1:
        ci('0')
      else:
        print("Error: Qty not valid")
        exit(-1)
      instancenames = list_instances(project, zone)
      if skipfullstartup == False:
        print("Waiting for instances to fully startup.")
        if len(instances) > 1:
          cis = functools.partial(check_instance_ssh, project, zone)
          pool = Pool(len(instancenames))
          pool.map(cis, instancenames)
          pool.close()
          pool.join()
        elif len(instances) == 1:
          check_instance_ssh(project, zone, instancenames.pop())
        else:
          print("Error: No instances found")
          exit(-1)
      else:
        print("NOTE: Skipped waiting for instances to fully startup.")
      print("Complete")

    elif mode == 'status':
      instancenames = list_instances(project, zone)
      if instancenames != False:
        cis = functools.partial(check_instance_ssh, project, zone)
        pool = Pool(len(instancenames))
        pool.map(cis, instancenames)
        pool.close()
        pool.join()
      else:
        print('No %s instances found in zone %s' % (project, zone))
      print("Complete")

    elif mode == 'make':
      instances = list_instances(project, zone)
      if instancenames != False:
        print('%s instances in zone %s:' % (project, zone))
        cmd = 'gcloud --project ' + project + ' compute config-ssh >/dev/null && '
        cmd += 'CCACHE_PREFIX=distcc DISTCC_HOSTS="'
        for instancename in instancenames:
            print(' - ' + instance)
            cmd += '@' + instance + '.' + zone + '.' + project + \
                   '/' + settings['mthreads']  + ',lzo --randomize '
        # Recommendation is to use 2x for j as actual cores
        cmd += '" make -j' + str(len(instancenames)*settings['mthreads']*2)
        #print cmd
        os.system(cmd) 
      else:
        print('No %s instances found in zone %s' % (project, zone))
      print("Complete")


    elif mode == 'stop':
      print('Deleting instance(s), this may take a few momments.')
      instancenames = list_instances(project, zone)
      if instancenames != False:
        di = functools.partial(delete_instance, project, zone)
        pool = Pool(len(instancenames))
        pool.map(di, instancenames)
        pool.close()
        pool.join()
      else:
        print('No %s instances found in zone %s' % (project, zone))
      print("Complete")

    else:
      print('Command not found, use one of: start, satus, make, stop')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='gdistcc',
        epilog="Copyright 2016 Andrew Peabody. See README.md for details.",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        'mode', 
        help='start: start gdistcc instances | status: check status of gdistcc instances | make: run make on gditcc instances | stop: stop gdistcc instances')
    parser.add_argument(
        '--settingsfile',
        default='./settings.json',
        help='Custom settings file. (default: %(default)s)')
    parser.add_argument(
        '--qty', 
        type=int,
        default=8, 
        help='Qty of Instances to deploy during start mode. (default: %(default)s)')
    parser.add_argument(
        '--skipfullstartup',
        dest='skipfullstartup', action='store_true',
        help='Skip waiting for full instance startup during start')
    parser.set_defaults(skipfullstartup=False)
    parser.add_argument(
        '--globalinstances',
        dest='globalinstances', action='store_true',
        help='Use all discovered instances for this prefix and distro, not just ones started by the local hosts')
    parser.set_defaults(globalinstances=False)
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 0.9-dev')

    args = parser.parse_args()

    # Set the settings file location globally
    global settingFile 
    settingsFile = args.settingsfile

    global globalinstances
    globalinstances = args.globalinstances

    # Sanity check for qty - limited to 8 during testing
    if 0 > args.qty or args.qty > 8:
        print("ERROR: Invalid qty: %s" % args.qty)
        exit(-1)

    main(args.qty, args.mode, args.skipfullstartup)
# [END run]
