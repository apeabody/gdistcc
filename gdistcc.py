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

from multiprocessing import Pool
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials
from six.moves import input


# [START list_instances]
def list_instances(project, zone):
    credentials = GoogleCredentials.get_application_default()
    compute = discovery.build('compute', 'v1', credentials=credentials)

    result = compute.instances().list(project=project, zone=zone).execute()
    return result['items'] if ('items' in result) else False
# [END list_instances]


# [START create_instance]
def create_instance(project, zone, name, distro, number):
    credentials = GoogleCredentials.get_application_default()
    compute = discovery.build('compute', 'v1', credentials=credentials)

    if "centos" in distro:
        compproj = 'centos-cloud'
    elif "ubuntu" in distro:
        compproj = 'ubuntu-os-cloud'
    else:
        print("ERROR: distro compute image family not found")
        exit(-1)

    image_response = compute.images().getFromFamily(
        project=compproj, family=distro).execute()
    source_disk_image = image_response['selfLink']

    # Configure the machine
    machine_type = "zones/%s/machineTypes/g1-small" % zone
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
    distro = platform.linux_distribution()[0].split()[0].lower() + '-' + \
             platform.linux_distribution()[1].split('.')[0]
    supportdistro = ['centos-7', 'ubuntu-1604-lts']
    if distro not in supportdistro:
      print('ERROR: %s is not a support distro' % distro)
      exit(-1)
    return distro
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
def main(project, zone, prefix, qty, mode, skipfullstartup):

    # Check the local distro version
    distro = check_distro()

    # Check the local gcc version
    gcc = check_gcc()

    # Check local distcc is present
    # subprocess.check_call(["distcc", "--version"])

    if mode == 'start':
      # Verify no current instances
      instances = list_instances(project, zone)
      if len(instances) > 0:
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
      instances = list_instances(project, zone)
      print('%s instances in zone %s:' % (project, zone))
      instancenames = []
      for instance in instances:
          print(' - ' + instance['name'])
          instancenames.append(instance['name'])
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
      instances = list_instances(project, zone)
      if instances:
        print('%s instances in zone %s:' % (project, zone))
        instancenames = []
        for instance in instances:
            print(' - ' + instance['name'])
            instancenames.append(instance['name'])
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
      if instances:
        print('%s instances in zone %s:' % (project, zone))
        cmd = 'gcloud --project ' + project + ' compute config-ssh >/dev/null && '
        cmd += 'CCACHE_PREFIX=distcc DISTCC_HOSTS="'
        for instance in instances:
            print(' - ' + instance['name'])
            cmd += '@' + instance['name'] + '.' + zone + '.' + project + \
                   '/1,lzo --randomize '
        # Recommendation is to use 2x for j as actual cores
        cmd += '" make -j' + str(len(instances)*2)
        #print cmd
        os.system(cmd) 
      else:
        print('No %s instances found in zone %s' % (project, zone))
      print("Complete")


    elif mode == 'stop':
      print('Deleting instance(s), this may take a few momments.')
      instances = list_instances(project, zone)
      if instances:
        print('%s instances in zone %s:' % (project, zone))
        instancenames = []
        for instance in instances:
            print(' - ' + instance['name'])
            instancenames.append(instance['name'])
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
        '--project',
        default='gdistcc',
        help='Google Cloud project ID. (default: %(default)s)')
    parser.add_argument(
        '--zone',
        default='us-central1-c',
        help='Compute Engine deploy zone. (default: %(default)s)')
    parser.add_argument(
        '--prefix', 
        default='gdistcc', 
        help='Instance prefix - generally no reason to change. %(default)s)')
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
        '--version',
        action='version',
        version='%(prog)s 0.9-dev')

    args = parser.parse_args()

    # Sanity check for qty - limited to 8 during testing
    if 0 > args.qty or args.qty > 8:
        print("ERROR: Invalid qty: %s" % args.qty)
        exit(-1)

    main(args.project, args.zone, args.prefix, args.qty, args.mode, args.skipfullstartup)
# [END run]
