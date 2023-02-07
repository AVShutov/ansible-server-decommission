from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
from ansible.plugins.inventory import BaseInventoryPlugin,Cacheable, Constructable
from ansible.errors import AnsibleError
from ansible.utils.display import Display

import re
import json
import os
import pdb
import sys

# add . to search path so we can find our common lib stuff
from os.path import dirname
sys.path.append(dirname(__file__))
import common

from python_libs.device42_api.Device42_API import Device42_API
from python_libs.device42_api.Device import Device

display = Display()

DOCUMENTATION = '''
    name: device42
    plugin_type: inventory
    author:
      - Patrick guan
    short_description: loads device42 inventory
    description:
       - device42 inventory
    options:
      plugin:
        required: true
        choices: ['device42']
        description: token to ensure using device42 plugin
      d42_user:
        description: device42 username
      d42_pass:
        description: device42 password
      d42_endpoint:
        description: device42 base URL

'''

EXAMPLES = '''
plugin: device42
d42_user: myuser
d42_pass: My_Users_Passw0rd
filters:
  tags_and:
    - puppet
    - tym
'''
class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):

  NAME = "device42"

  def __init__(self):
    super(InventoryModule, self).__init__()
    self.api = None


  def verify_file(self, path):
    if super(InventoryModule, self).verify_file(path):
      if path.endswith(('d42.yml', 'd42.yaml')):
        return True
    display.debug("d42 inventory filename must end with 'd42.yml' or 'd42.yaml'")
    return False


  def parse(self, inventory, loader, path, cache=True):
    super(InventoryModule, self).parse(inventory, loader, path, cache)
    config = self._read_config_data(path)
    self.display.vvv('{}'.format(config))

    self.dologin(path)

    params = {}
    for f in config['filters']:
      if isinstance(config['filters'][f], list):
        params[f] = ','.join(config['filters'][f])
      else:
        params[f] = config['filters'][f]

    self.display.vvv('{}'.format(params))
    try:
      device = Device.search(self.api, params)
      self.display.vvvvv(device)
    except Exception as e:
      self.display.error(e)
      exit


    self.parse_json(device)


  def dologin(self, path):
    # setup device42
    d42_user = self.get_option('d42_user')
    if d42_user == '' or d42_user == None:
      d42_user = os.environ['D42_USERNAME']
      if d42_user == '' or d42_user == None:
        d42_user = os.environ['USERNAME']
        if d42_user == '' or d42_user == None:
          d42_user = input("Device42 user not set, Please enter:")

    d42_pass = self.get_option('d42_pass')
    # stringify value if it was vault encrypted
    d42_pass = str(d42_pass)
    if d42_pass == '' or d42_pass == None or d42_pass == "None":
      d42_pass = os.environ['D42_PASSWORD']
      if d42_pass == '' or d42_pass == None or d42_pass == "None":
        d42_pass = os.environ['PASSWORD']
        if d42_pass == '' or d42_pass == None or d42_pass == "None":
          d42_pass = input("Device42 password not set, Please enter:")

    d42_endpoint = self.get_option('d42_endpoint')
    if d42_endpoint == '' or d42_endpoint == None or d42_endpoint == "None":
      d42_endpoint = "https://device42.example.com/"

    # self.api = Device42_API(d42_endpoint, (50 - (10 * self.display.verbosity))) # do this when we figure out how to pass a logging object down that'll use the ansible logs
    self.api = Device42_API(d42_endpoint)

    if self.api.is_authenticated() and self.api.is_config_dirty() == False:
      return True
    else:
      res = self.api.authenticate(username=d42_user, password=d42_pass)
      if res == False:
        raise AnsibleError('d42 login failed')
      else:
        return True

  # parses device names from device 42 devices api json response
  def parse_json(self, inventory):
    self.display.vvv('{}'.format(inventory))
    try:
      j1 = json.loads(inventory)
    except:
      #if inventory is an already parsed into python object
      j1 = inventory

    try:
      devices = j1["Devices"]
    except:
      raise AnsibleError("Device42 response missing Devices")

    device_names = [x['name'] for x in devices]
    for i in range(len(device_names)):
      name = device_names[i]
      if 'example.com' not in name:
        device_names[i] = name+'.example.com'
    for h in device_names:
      groups = common.parsehost(h)
      for g in groups:
        g=g.lower()
        h=h.lower()
        self.inventory.add_group(g)
        self.inventory.add_host(h,group=g)
