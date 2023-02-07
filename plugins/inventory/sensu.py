__metaclass__ = type
from ansible.plugins.inventory import BaseInventoryPlugin,Cacheable, Constructable
from ansible.errors import AnsibleError
from ansible.utils.display import Display
display = Display()

import os
import sys
import re
import requests

# add . to search path so we can find our common lib stuff
from os.path import dirname
sys.path.append(dirname(__file__))
import common as lib

DOCUMENTATION = r'''
    inventory: sensu
    version_added: "2.4"
    short_description: Parses a 'sensu api query' string (of sorts)
    description:
        - Parses a host string with keywords to do a lookup.
        - This plugin only applies to inventory strings that are not paths and begin with the module's name.
        - Possible parameters are `check`, `event`, `state`, and `operator`.
        - check and `event` are both the names of checks defined in sensu, but the events api returns MUCH faster than the checks api, so check should only be used in cases where there's not an event (e.g. the check isn't failing).
        - state is the expected state of the check to operate on (OK, WARN, FAIL, UNKNOWN, etc).
        - operator is the operation to perform `<`, `>`, `=`, etc.
'''

EXAMPLES = r'''
To restart the puppet agent on all machines with a failing puppet run
# ansible-playbook -i 'sensu:check=CORE_puprun,operator=>,state=OK' ~/Code/stash.example.com/ANSB/role-puppet/tasks/restart-agent.yml
'''

SENSU_API = 'sensu-aws.example.com:4567'
EVENTS_API = "http://{}/events".format(SENSU_API)
RESULTS_API = "http://{}/results".format(SENSU_API)
CLIENTS_API = "http://{}/clients".format(SENSU_API)

SENSU_OK = 0
SENSU_WARNING = 1
SENSU_ERROR = 2

class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):

  NAME = 'sensu'

  def __init__(self):
    self.check = None
    super(InventoryModule, self).__init__()

  def verify_file(self, path):
    # if it starts with sensu:
    if lib.verify_path(self.NAME, path):
      return True

    # see if we have a .pdb.yaml file
    if super(InventoryModule, self).verify_file(path):
      if path.endswith(('sensu.yaml')):
        return True

    display.debug("puppet sensu inventory filename must end with 'sensu.yaml'")
    return False


  def parse(self, inventory, loader, path, cache=True):
    self.loader = loader
    self.inventory = inventory

    try: # the default ansible parser for yaml file values
      super(InventoryModule, self).parse(inventory, loader, path, cache)
      params = self._read_config_data(path)

    except Exception: # we're passing values with input string
      params = lib.parse_path(self.NAME, path)

    results = self._get_results_from_api(params)
    for host in results:
      if self.check != None:
        self.inventory.add_group(self.check)
        self.inventory.add_host(host, group=self.check)
      groups = lib.parsehost(host)
      host = lib.get_lan_hostname(host)
      self.display.vvvv("adding host: {}".format(host))
      for g in groups:
        self.inventory.add_group(g)
        self.inventory.add_host(host,group=g)

  def _get_results_from_api(self, params):
    if 'check' in params:
      check = params['check']
    else:
      check = None

    if 'event' in params:
      check = params['event']
    else:
      if not check:
        check = None
    self.display.vvvv('check: {}'.format(check))

    if 'state' in params:
      state = params['state']
    else:
      state = 'ERROR'
    self.display.vvvv('state: {}'.format(state))

    if 'operator' in params:
      operator = params['operator']
    else:
      operator = '='
    self.display.vvvv('operator: {}'.format(operator))

    self.display.vvv('checking type')
    self.check = check
    if 'event' in params:
      self.display.vvv("looking for hosts_with_event")
      return self.hosts_with_event(check=check, state=state, operator=operator)
    elif 'check' in params:
      self.display.vvv('looking for hosts_with_check')
      return self.hosts_with_check(check=check, state=state, operator=operator)
    else:
      return self.all_sensu_clients()


  '''
  hosts_with_event and hosts_with_check will return similar data with drastic differences in the amount of time it takes them to run

  fab -R 'sensu_check:CORE_puprun>OK' l
  and
  fab -R 'sensu_event:CORE_puprun' l
  will return the same results, with the former taking ~10x as long as the latter

  hosts_with_check should only be used if you want to return only hosts in an OK state, or all hosts with the check
  hosts_with_event should be used if you want to find hosts with issues
  '''


  def hosts_with_event(self, check='', state='ERROR', operator='='):
      '''
      Get a list of hosts with a specific check on them in a non-OK state, optionally in a specific given state

      example:
        TBD
      '''
      if operator == '=':
        operator = '=='


      self.display.vvv('in hosts_with_event')
      self.display.vvvv('check={}, state={}, operator={}'.format(check, state, operator))

      state_val = SENSU_OK
      if state:
          if re.search('^WARN(ING)?', state):
              state_val = SENSU_WARNING
          elif re.search('^(ERR(OR)?|CRIT(ICAL)?)', state):
              state_val = SENSU_ERROR

      url = "{}?filter.check.name={}".format(EVENTS_API, check)
      self.display.vvv("state_val: {}".format(state_val))
      self.display.vvv('about to hit api call ({})'.format(url))

      try:
        r = requests.get( url, timeout=5 )  # , verify=False
      except TimeoutError:
        self.display.error("web request timed out")
        return {}

      self.display.vvv("response from api call: {}".format(r))

      ret = []
      for event in r.json():
          self.display.vvvvvv("Host {} -- Check: {} -- State: {}".format(event['client']['name'], event['check']['name'], event['check']['status']))
          if event['check']['name'] == check:
            if eval("{} {} {}".format(event['check']['status'], operator, state_val)):
              self.display.vvvvvv("adding {} to host list".format(event['client']['name']))
              ret.append(event['client']['name'])

      return ret


  def hosts_with_check(self, check, state='ERROR', operator='='):
      '''
      Get a list of hosts with a specific check on them, optionally in a given state
      '''

      if operator == '=':
          operator = '=='

      state_val = 0
      if state:
          if re.search('^WARN(ING)?', state):
              state_val = SENSU_WARNING
          elif re.search('^(ERR(OR)?|CRIT(ICAL)?)', state):
              state_val = SENSU_ERROR
          elif re.search('^OK', state):
              state_val = SENSU_OK

      ret = []
      url = "{}?filter.check.name={}".format(RESULTS_API, check)
      r = requests.get( url )  # , verify=False)
      for event in r.json():
          if event['check']['name'] == check:
              if state:
                  if eval("{} {} {}".format(event['check']['status'], operator, state_val)):
                      ret.append(event['client'])
              else:
                  ret.append(event['client'])

      return ret

  def all_sensu_clients(self):
      '''
      Get a list of all sensu clients
      '''

      ret = []
      r = requests.get( CLIENTS_API )  # , verify=False)
      for client in r.json():
        ret.append(client['name'])

      return ret
