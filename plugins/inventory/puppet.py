__metaclass__ = type

import os
import re
import sys
import socket
import inspect
import pypuppetdb
import hashlib

from ansible.plugins.inventory import BaseInventoryPlugin,Cacheable, Constructable
from ansible.errors import AnsibleError
from ansible.utils.display import Display
display = Display()

# add . to search path so we can find our common lib stuff
from os.path import dirname
sys.path.append(dirname(__file__))
import common as lib



DOCUMENTATION = r'''
    inventory: puppet
    version_added: "2.4"
    short_description: Parses a 'puppetdb query' string (of sorts)
    description:
        - Parses a host string with keywords to do a lookup
        - This plugin only applies to inventory strings that are not paths and begin with the module's name
'''

EXAMPLES = r'''
To restart the puppet agent on all puppetdb servers
# ansible-playbook -i 'puppet:class=roles::cloudops::puppet::database' ~/Code/stash.example.com/ANSB/role-puppet/tasks/restart-agent.yml

To do the same on all physical nodes, skipping virtual machines
# ansible-playbook -i 'puppet:fact=virtual,value=physical' ~/Code/stash.example.com/ANSB/role-puppet/tasks/restart-agent.yml

'''


PUPPETDB_API = 'puppetdb0.example.com'

hostname = socket.gethostname()
pdb_ssl_ca = '/etc/puppetlabs/puppet/ssl/certs/ca.pem'
pdb_ssl_cert = '/etc/puppetlabs/puppet/ssl/certs/{}.pem'.format(hostname)
pdb_ssl_key = '/etc/puppetlabs/puppet/ssl/private_keys/{}.pem'.format(hostname)

if os.getenv('FABRIC_PDB_CA', False):
    pdb_ssl_ca = os.getenv('FABRIC_PDB_CA')
if os.getenv('FABRIC_PDB_SSL_CERT', False):
    pdb_ssl_cert = os.getenv('FABRIC_PDB_SSL_CERT')
if os.getenv('FABRIC_PDB_SSL_KEY', False):
    pdb_ssl_key = os.getenv('FABRIC_PDB_SSL_KEY')

def connect_pdb():
  pdb = pypuppetdb.connect(
      host=PUPPETDB_API,
      port='8081',
      ssl_verify=pdb_ssl_ca, ssl_key=pdb_ssl_key, ssl_cert=pdb_ssl_cert,
  )

  return pdb


class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):

  NAME = 'puppet'

  def parse(self, inventory, loader, path, cache=True):
    self.loader = loader
    self.inventory = inventory

    self.display.vvv("FABRIC_PDB_CA: " + str(hashlib.sha256(open(os.environ['FABRIC_PDB_CA']).read().encode('utf-8')).hexdigest()))
    self.display.vvv("FABRIC_PDB_SSL_CERT: " + str(hashlib.sha256(open(os.environ['FABRIC_PDB_SSL_CERT']).read().encode('utf-8')).hexdigest()))
    self.display.vvv("FABRIC_PDB_SSL_KEY: " + str(hashlib.sha256(open(os.environ['FABRIC_PDB_SSL_KEY']).read().encode('utf-8')).hexdigest()))

    try: # the default ansible parser for yaml file values
      super(InventoryModule, self).parse(inventory, loader, path, cache)
      params = self._read_config_data(path)

    except Exception: # we're passing values with input string
      params = lib.parse_path(self.NAME, path)

    self.display.vvv('{}'.format(params))
    results = self._get_results_from_api(params)
    for host in results:
      groups = lib.parsehost(host)
      host = lib.get_lan_hostname(host)
      for g in groups:
        self.inventory.add_group(g)
        self.inventory.add_host(host,group=g)

  def verify_file(self, path):
    # if it starts with puppet:
    if lib.verify_path(self.NAME, path):
      return True

    # see if we have a .pdb.yaml file
    if super(InventoryModule, self).verify_file(path):
      if path.endswith(('pdb.yaml')):
        return True
    display.debug("puppet db inventory filename must end with 'pdb.yaml'")
    return False


  def _get_results_from_api(self, params):
    self.display.vvv('getting results from api {0.filename}@{0.lineno}:'.format(inspect.getframeinfo(inspect.currentframe())))
    self.display.vvv('checking type')
    if 'regex' in params:
      self.display.vvv("looking for hosts_with_regex")
      return self.hosts_regex(regex=params['regex'])
    elif 'class' in params:
      self.display.vvv('looking for hosts_with_class')
      return self.hosts_with_class(classname=params['class'])
    elif 'fact' in params and 'value' in params:
      self.display.vvv('looking for hosts_with_fact')
      return self.hosts_with_fact(fact_name=params['fact'], fact_value=params['value'])
    elif 'resource' in params:
      self.display.vvv('looking for hosts_with_resource')
      return self.hosts_with_resource(resource=params['resource'])
    else:
      return []

  def hosts_with_class(self, classname):
    '''
    get all hosts including a class
    '''
    pdb = connect_pdb()
    class_parts = classname.split('::')
    self.display.vvv('Class Parts: {}'.format(class_parts))
    class_parts = [x.capitalize() for x in class_parts]
    self.display.vvv('Class Parts: {}'.format(class_parts))

    classname = "::".join(class_parts)
    self.display.vvv('classname: {}'.format(classname))

    nodes = pdb.resources('Class', classname)
    # print nodes
    return [lib.get_lan_hostname(node.node) for node in nodes]


  def hosts_with_resource(self, resource, name=None):
      '''
      get all hosts with a resource defined
      if name is set, will only get hosts with Resource['name']
      '''
      pdb = connect_pdb()
      nodes = pdb.resources(resource, name)
      # print name
      # print resource
      return [lib.get_lan_hostname(node.node) for node in nodes]


  def hosts_with_fact(self, fact_name, fact_value, operator='='):
      '''
      get all hosts where fact_name == fact_value
      '''
      pdb = connect_pdb()
      self.display.vvv("searching for fact {} with value {}".format(fact_name, fact_value))
      nodes = pdb.facts(fact_name, fact_value)
      return [lib.get_lan_hostname(node.node) for node in nodes]


  def hosts_regex(self, regex=".*"):
      '''
      get all hosts where the hostname matches a given regex
      (default matches everything)
      '''
      pdb = connect_pdb()
      nodes = pdb.nodes()
      return [lib.get_lan_hostname(node.name) for node in nodes if re.match(regex, node.name)]

if __name__ == '__main__':
    inventory = {}
    enterprise = {}

    # return to ansible
    sys.stdout.write(str(inventory))
    sys.stdout.flush()


