# Ansible inventory plugin using LibreNMS 
#
# Dao Che, 2020-3-2
# 

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
from ansible.plugins.inventory import BaseInventoryPlugin,Cacheable, Constructable
from ansible.errors import AnsibleError
from ansible.utils.display import Display

import sys
import os
import shutil
import json
import requests
import argparse
import re
from ansible.module_utils._text import to_native

# add . to search path so we can find our common lib stuff
from os.path import dirname
sys.path.append(dirname(__file__))
import common

display = Display()

DOCUMENTATION = '''
    name: nms
    plugin_type: inventory
    author:
      - Dao Che
    short_description: loads nms inventory
    description:
       - nms inventory
    options:
      plugin:
        required: true
        choices: ['nms']
        description: token to ensure using nms plugin
      api_user:
        description: nms username
      api_pw:
        description: nms password
      api_endpoint:
        description: nms endpoint
      api_key:
        description: nms api key
'''

EXAMPLES = '''
plugin: nms
api_user: rancid
api_pw: xxxxxxxxxxxx
api_endpoint: https://nms1.example.com/api/v0/devices
api_key: xxxxxxxxxxxxxxx
'''

class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
  NAME = "nms"

  def __init__(self):
    super(InventoryModule, self).__init__()
    self.api = None


  def verify_file(self, path):
    if super(InventoryModule, self).verify_file(path):
      if path.endswith(('nms.yml', 'nms.yaml')):
        return True
    display.debug("nms inventory filename must end with 'nms.yml' or 'nms.yaml'")
    return False

  def parse(self, inventory, loader, path, cache=True):
    super(InventoryModule, self).parse(inventory, loader, path, cache)
    config = self._read_config_data(path)
    self.display.vvv('{}'.format(config))

    self.get_nms()

  def libresNMS(self, api_endpoint, api_key, userid, password):
    switch = { "arista_eos": "eos" }
    s = requests.Session()
    s.auth = (userid, password)
    headers = { 'X-Auth-Token': api_key, }

    try:
      r = s.get(api_endpoint, headers=headers)
      devices = json.loads(r.text)

    except Exception as e:
       display.debug("Something is wrong. NMS not returning valid devices. Check API_URL, API_KEY, API_USER, and API_PASSWORD. %s" % to_native(e))
       return

    for device in devices['devices']:
        nms_os = re.match("^([a-zA-Z]*).*", device['os']).group(0)
        ansible_network_os = switch.get(nms_os, nms_os)
        
        try:
          hostname = device['hostname']
          groups = common.parsehost(hostname)

          for g in groups:
            g=g.lower()
            h=hostname.lower()
            self.inventory.add_group(g)
            self.inventory.add_host(h,group=g)

          self.inventory.add_group(ansible_network_os)
          self.inventory.add_host(h, group=ansible_network_os)

        except KeyError:
           self.inventory.add_group(ansible_network_os)

    return

  def getArgs(self):
    # setup LibresNMS API 
    api_user = self.get_option('api_user')
    if api_user == '' or api_user is None:
       try:
         api_user = os.environ['USERNAME']
       except:
         api_user = input("LibreNMS user not set, Please enter:")

    api_pw = self.get_option('api_pw')
    api_pw = str(api_pw)
    if api_pw == '' or api_pw == None or api_pw == "None":
       try:
         api_pw = os.environ['PASSWORD']
       except: 
          api_pw = input("LibreNMS password not set, Please enter:")

    api_endpoint = self.get_option('api_endpoint')
    if api_endpoint == '' or api_endpoint == None or api_endpoint == "None":
      try:
         api_endpoint = os.environ['NMS_ENDPOINT']
      except:
         api_endpoint = input("LibreNMS api_endpoint not set, Please enter:")

    api_key = self.get_option('api_key')
    if api_key == '' or api_key is None or api_key == "None":
       try:
          api_key = os.environ['NMS_KEY']
       except:
          api_key = input("LibreNMS api_key not set, Please enter:")

    return (api_endpoint, api_key, api_user, api_pw)

  
  def get_nms(self):
    err = """
        @
        @ ERROR!!! missing required variables: api_endpoint, api_key, api_user, api_pw
        @
        """
    (api_endpoint, api_key, api_user, api_pw) = self.getArgs()

    if api_endpoint is None: api_endpoint = os.getenv('API_URL', None)
    if api_key is None: api_key = os.getenv('API_KEY', None)
    if api_user is None: api_user = os.getenv('API_USER', None)
    if api_pw is False: api_pw = os.getenv('API_PASSWORD', None)

    if api_endpoint is None or api_key is None or api_user is None or api_pw is None:
       display.debug(err)
       exit (1)

    self.libresNMS(api_endpoint, api_key, api_user, api_pw)
    return
