import os
import re
import socket

def get_lan_hostname(hostname):
    ret = hostname
    new_hostname = hostname
    index = 0
    prefixes = ['lan', 'vlan10', 'eth1', 'eth0', ]
    resolved_ip = ''

    while True:
        try:
            resolved_ip = socket.gethostbyname(new_hostname)
        except socket.gaierror:
            pass

        if re.match('^10\.', resolved_ip):
            ret = new_hostname
            break
        if index >= len(prefixes):
            break

        new_hostname = '%s.%s' % (prefixes[index], hostname)
        index = index+1

    return ret

def verify_path(module, path):
    ''' return true/false if this is possibly a valid file for this plugin to consume '''
    valid = False
    path = re.sub('{}/'.format(os.environ['PWD']), '', path)
    if path.startswith((module)):
      valid = True

    return valid

def parse_path(module, path):
    # strip module_name and split path into kv pairs
    restr = '^{}:'.format(module)
    path = re.sub('{}/'.format(os.environ['PWD']), '', path)
    param_string = re.sub(restr, '', path)
    param_string = re.sub(',$', '', param_string)
    params = {}

    if re.search(',', param_string):
        param_pairs = param_string.split(',')
    else:
        param_pairs = [ param_string ]
  
    for pair in param_pairs:
        k, v = pair.split('=')
        if k:
            params[k] = v

    return params

# creates groups based on civ2 puppet style fqdn splitting  
def parsehost(hostname):
    host = hostname.replace('example.com','').lower()

    try:
      split_host = host.split('.')
      if len(split_host) == 4:
        subnode = split_host[1]
        del split_host[1]
      else:
        subnode = None

      node = split_host[0]
      product = split_host[1]
      site = split_host[2]
      match = re.search(r'\d', node)
      if match != None:
        number_start = match.start()
        node_name = node[:number_start]
        node_number = node[number_start:]
      else:
        node_number = None
        node_name = node

      groups = [node_name,product,site]
      if subnode != None:
        groups = [node_name,product,site,subnode]
      else:
        groups = [node_name,product,site]
    except:
        # catch exceptions with indexes out of range when trying to parse hostname
        groups = ['ungrouped']
      
        
    groups = [g for g in groups if g != '']
    return groups
