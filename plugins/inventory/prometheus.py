#!/usr/bin/env python3
import sys

from ansible.plugins.inventory import BaseInventoryPlugin, Constructable, Cacheable

class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):

  NAME = 'myplugin'

  def parse():
    self.inventory.add_host('puppet0.example.com')

  def verify_file(self, path):
      ''' return true/false if this is possibly a valid file for this plugin to consume '''
      valid = False
      if super(InventoryModule, self).verify_file(path):
          # base class verifies that file exists and is readable by current user
          if path.endswith(('virtualbox.yaml', 'virtualbox.yml', 'vbox.yaml', 'vbox.yml', 'something')):
              valid = True
      return valid

if __name__ == '__main__':
    inventory = {}
    enterprise = {}

    # return to ansible
    sys.stdout.write(str(inventory))
    sys.stdout.flush()