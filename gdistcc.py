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
def create_instance(project, zone, name, number):
    credentials = GoogleCredentials.get_application_default()
    compute = discovery.build('compute', 'v1', credentials=credentials)

    image_response = compute.images().getFromFamily(
        project='centos-cloud', family='centos-7').execute()
    source_disk_image = image_response['selfLink']

    # Configure the machine
    machine_type = "zones/%s/machineTypes/g1-small" % zone
    startup_script = open(
        os.path.join(
            os.path.dirname(__file__), 'startup-scripts/centos-7.sh'), 'r').read()

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


# [START run]
def main(project, zone, name, qty, function, waitonssh):
    if function == 'start':
      print('Creating %s %s instances, this will take a few momments.' % (qty, project))
      if qty > 1:
        ci = functools.partial(create_instance, project, zone, name)
        pool = Pool(qty)
        pool.map(ci, xrange(qty))
        pool.close()
        pool.join()
      elif qty == 1:
        create_instance(project, zone, name, 1)
      else:
        print("Error: Qty not valid")
        exit(-1)
      instances = list_instances(project, zone)
      print('%s instances in zone %s:' % (project, zone))
      instancenames = []
      for instance in instances:
          print(' - ' + instance['name'])
          instancenames.append(instance['name'])
      if waitonssh == True:
        print("NOTE: It may take several minutes waiting for the instances to fully setup.")
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
        print("NOTE: It may take several minutes for the instances to fully setup.")
      print("Complete")

    elif function == 'status':
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

    elif function == 'make':
      instances = list_instances(project, zone)
      if instances:
        print('%s instances in zone %s:' % (project, zone))
        cmd = 'gcloud --project ' + project + ' compute config-ssh && '
        cmd += 'DISTCC_TCP_CORK=0 CCACHE_PREFIX=distcc DISTCC_HOSTS="'
        for instance in instances:
            print(' - ' + instance['name'])
            cmd += '@' + instance['name'] + '.' + zone + '.' + project + \
                   '/2,lzo,cpp '
        # Recommendation is to use 2x for j as actual cores
        cmd += '" pump make -j' + str(len(instances)*2)
        #print cmd
        os.system(cmd) 
      else:
        print('No %s instances found in zone %s' % (project, zone))
      print("Complete")


    elif function == 'stop':
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
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        'function', 
        help='start,status,make,stop')
    parser.add_argument(
        '--project',
        default='gdistcc',
        help='Google Cloud project ID.')
    parser.add_argument(
        '--zone',
        default='us-central1-c',
        help='Compute Engine deploy zone.')
    parser.add_argument(
        '--name', 
        default=str('gdistcc-{}').format(str(uuid.uuid4())[:8]), 
        help='Instance name.')
    parser.add_argument(
        '--qty', 
        default=1, 
        help='Qty of Instances to deploy.')
    parser.add_argument(
        '--waitonssh',
        dest='waitonssh', action='store_true',
        help='Set to True to wait for ssh on startup.')
    parser.set_defaults(waitonssh=False)
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 0.9')

    args = parser.parse_args()

    main(args.project, args.zone, args.name, int(args.qty), args.function, args.waitonssh)
# [END run]
