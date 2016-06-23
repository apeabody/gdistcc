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

# [START wait_operation]
def wait_operation(operation):

    # NOT thread safe
    credentials = GoogleCredentials.get_application_default()
    compute = discovery.build('compute', 'v1', credentials=credentials)

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
# [END wait_operation]


# [START list_instances]
def list_instances(project, zone, globalinstances, distro, includeterm):

    # NOT thread safe
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
            if name in instance['name']:
                print(' - ' + instance['name'] + ' - ' + instance['status'])
                if (instance['status'] == 'RUNNING' or includeterm): 
                    instancenames.append(instance['name'])
        return instancenames if (len(instancenames) > 0) else False
    return False
# [END list_instances]


# [START check_gceproject]
def check_gceproject(distro, settingsFile):
    with open(settingsFile) as distros_file:
      distros = json.load(distros_file)['distros']

    for distrol in distros:
      if distrol['name'] == distro:
        return distrol['gceproject']
    print("ERROR: distro compute image family not found")
    exit(-1)
# [END check_gceproject]


# [START create_instance]
def create_instance(project, zone, name, source_disk_image, mtype, distro, number):

    # Unfortunatly this is NOT thread safe
    credentials = GoogleCredentials.get_application_default()
    compute = discovery.build('compute', 'v1', credentials=credentials)

    # Configure the machine
    machine_type = "zones/%s/machineTypes/%s" % (zone, mtype)
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

    return wait_operation(operation)
# [END create_instance]


# [START check_instance]
def check_instance_ssh(project, zone, name):
    for i in xrange(40):
        
        sys.stdout.write(".")
        sys.stdout.flush()

        cicmd = 'gcloud compute ssh ' + name + \
               ' --zone ' + zone + \
               ' --project ' + project + \
               ' --command "cat /tmp/gdistcc_ready" | grep GDISTCC_READY || true'
 
        result = subprocess.check_output(cicmd, shell=True, stderr=open(os.devnull, 'w'))
                
        if "GDISTCC_READY" in result:
            print('\r - ' + name + ' - ready')
            return True 

        time.sleep(10)
     
    print('WARNING: ' + name + ' did not complete setup in a reasonable time.')
    return False
# [END check_instance]


# [START delete_instance]
def delete_instance(project, zone, name):
    # NOT thread safe
    credentials = GoogleCredentials.get_application_default()
    compute = discovery.build('compute', 'v1', credentials=credentials)

    # Delete the instance
    operation = compute.instances().delete(
        project=project,
        zone=zone,
        instance=name).execute()

    return wait_operation(operation)
# [END delete_instance]


# [START check_distro]
def check_distro(settingsFile):
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


# [START main]
def main():

    parser = argparse.ArgumentParser(
        prog='gdistcc',
        epilog="Copyright 2016 Andrew Peabody. See README.md for details.",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        'mode',
        choices=['start','status','make','stop'])
    parser.add_argument(
        '--settingsfile',
        default=os.path.dirname(os.path.realpath(__file__)) + '/settings.json',
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
        version='%(prog)s 0.9.3')

    args = parser.parse_args()

    # Sanity check for qty - limited to 8 during testing
    if 0 > args.qty or args.qty > 8:
        print("ERROR: Invalid qty: %s" % args.qty)
        exit(-1)

    qty = args.qty
    mode = args.mode
    skipfullstartup = args.skipfullstartup
    globalinstances = args.globalinstances

    # Check the local distro version
    distro = check_distro(args.settingsfile)

    # Load settings - move to function later
    gcc = check_gcc()

    # Set the settings file location globally
    with open(args.settingsfile) as distros_file:
      settings = json.load(distros_file)['settings']
    global project
    project = settings['project']
    global zone
    zone = settings['zone']
    global prefix
    prefix = settings['prefix']
    mtype = settings['mtype']

    # NOT thread safe
    credentials = GoogleCredentials.get_application_default()
    compute = discovery.build('compute', 'v1', credentials=credentials)

    if mode == 'start':
      # Verify no current instances
      instances = list_instances(project, zone, globalinstances, distro, False)
      if instances != False:
        print('ERROR: %s gdistcc instance(s) detected, run \'gdistcc status\' for details' % len(instances))
        exit(-1)
      name = prefix + '-' + distro + '-' + format(str(uuid.getnode())[:8:-1])

      image_response = compute.images().getFromFamily(
          project=check_gceproject(distro, args.settingsfile), family=distro).execute()
      source_disk_image = image_response['selfLink']

      print('Creating %s %s instances, this will take a few momments.' % (qty, project))
      ci = functools.partial(create_instance, project, zone, name, source_disk_image, mtype, distro)
      if qty > 1:
        pool = Pool(qty)
        pool.map(ci, xrange(qty))
        pool.close()
        pool.join()
        print('\n')
      # useful during testing to avoid map
      elif qty == 1:
        ci('0')

    if mode == 'status' or mode == 'start':
      instancenames = list_instances(project, zone, globalinstances, distro, False)
      if instancenames != False and skipfullstartup == False:
        cis = functools.partial(check_instance_ssh, project, zone)
        pool = Pool(len(instancenames))
        pool.map(cis, instancenames)
        pool.close()
        pool.join()
      else:
        print('No %s running instances found in zone %s' % (project, zone))
      print("Complete")

    elif mode == 'make':
      instancenames = list_instances(project, zone, globalinstances, distro, False)
      if instancenames != False:
        cmd = 'gcloud --project ' + project + ' compute config-ssh &>/dev/null && '
        cmd += 'CCACHE_PREFIX=distcc DISTCC_HOSTS="'
        for instancename in instancenames:
            cmd += '@' + instancename + '.' + zone + '.' + project + \
                   '/' + settings['mthreads']  + ',lzo '
        # Randomize the order we use the instances
        cmd += '--randomize" '
        # Recommendation is to use 2x for j as actual cores
        cmd += 'make -j' + str(len(instancenames)*int(settings['mthreads'])*2)
        os.system(cmd) 
      else:
        print('No %s instances found in zone %s' % (project, zone))
      print("Complete")


    if mode == 'stop':
      print('Deleting instance(s), this may take a few momments.')
      instancenames = list_instances(project, zone, globalinstances, distro, True)
      if instancenames != False:
        di = functools.partial(delete_instance, project, zone)
        pool = Pool(len(instancenames))
        pool.map(di, instancenames)
        pool.close()
        pool.join()
      else:
        print('No %s instances found in zone %s' % (project, zone))
      print('\n' + "Complete")
# [END main]

if __name__ == '__main__':
    main()

