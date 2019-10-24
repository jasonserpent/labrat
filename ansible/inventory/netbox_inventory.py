#!/usr/bin/env python

# References:
# Developing dynamic inventory:
#   https://docs.ansible.com/ansible/latest/dev_guide/developing_inventory.html
# pynetbox API:
#  https://pynetbox.readthedocs.io/en/latest/index.html


import sys
import os
import getopt
import json
import yaml
import pynetbox

#from ansible.parsing.vault import VaultLib, get_file_vault_secret, is_encrypted_file
#from ansible.parsing.yaml.loader import AnsibleLoader
#from ansible.parsing.dataloader import DataLoader

NETBOX_URL = 'http://netbox.lon.eplus.lab/'
MANUFACTURERS = ['arista', 'cisco', 'juniper']
DEVICE_ROLES = ['testswitch', 'testrouter', 'infrastructurenetwork', 'testfirewall']



#INVENTORY_PATH = '/home/pedro/Eplus/labuk/ansible/inventory/'
INVENTORY_PATH = './inventory/'

nb = pynetbox.api(NETBOX_URL)

def _fetch_nb_endpoints(**kwargs):
    global manufacturers
    global sites
    global roles
    global devices

    # If not arguments are passed we fetch at once all endpoints
    # We do still filter the 'interesting' ones
    if not kwargs:
        try:
            manufacturers = _filter_manufacturers(nb.dcim.manufacturers.all())
        except:
            manufacturers = []
        sites = nb.dcim.sites.all()
        roles = _filter_roles(nb.dcim.device_roles.all())
        #devices = _filter_devices(nb.dcim.devices.all())
        # status=1 means all Active devices
        devices = _filter_devices(nb.dcim.devices.filter(status=1))
        return

    # Otherwise we expect a single hostname
    for key in kwargs:
        if key not in ['hostname']:
            raise Exception('_fetch_nb_endpoints wrong arguments')

    hostname = kwargs['hostname']
    manufacturers = []
    sites = []
    roles = []
    devices = []

    device = nb.dcim.devices.filter(name=hostname)[0]
    manufacturer = nb.dcim.manufacturers.filter(slug=device.device_type.manufacturer.slug)[0]
    site = nb.dcim.sites.filter(slug=device.site.slug)[0]
    role = nb.dcim.device_roles.filter(slug=device.device_role.slug)[0]

    devices.append(device)
    manufacturers.append(manufacturer)
    sites.append(site)
    roles.append(role)


def _print_inventory(inventory):
    print(json.dumps(inventory, indent=4))

def _load_yaml_vars(filename):
    filename = INVENTORY_PATH + filename
    if os.path.isfile(filename):
        try:
            with open(filename) as v_file:
                y_vars = yaml.safe_load(v_file)
                if y_vars:
                    return y_vars
                return {}
        except IOError:
            return {}
    return {}


def _get_device_by_name(devices, name):
    for device in devices:
        if str(device) == name:
            return device


def _filter_devices(devices, role_slugs=DEVICE_ROLES, manufacturer_slugs=MANUFACTURERS, **kwargs):
    # This inventory is only interested in some roles and manufacturers names
    # By default we do not filter based on the site name

    if type(role_slugs) is not list: role_slugs = [ role_slugs ]
    if type(manufacturer_slugs) is not list: manufacturer_slugs = [ manufacturer_slugs ]

    for key in kwargs:
        if key not in ['site_slugs']:
            raise Exception('_filter_devices wrong arguments')

    if 'site_slugs' in kwargs.keys():
        site_slugs = kwargs['site_slugs']
        if type(site_slugs) is not list: site_slugs = [ site_slugs ]
        return list(
                filter(
                    lambda x: x.device_role.slug in role_slugs
                            and x.device_type.manufacturer.slug in manufacturer_slugs
                            and x.site.slug in site_slugs,
                    devices
                )
        )

    return list(
            filter(
                lambda x: x.device_role.slug in role_slugs
                        and x.device_type.manufacturer.slug in manufacturer_slugs,
                devices
            )
    )


def _filter_roles(roles, slugs=DEVICE_ROLES):
    # This inventory is only interested in the following roles
    return list(filter(lambda x: x.slug in slugs, roles))

def _get_object_by_id(objects, id):
    for object in objects:
        if object.id == id:
            return object

def _get_object_by_name(objects, name):
    for object in objects:
        if str(object) == name:
            return object

def _filter_manufacturers(manufacturers, slugs=MANUFACTURERS):
    # This inventory is only interested in the following manufacturers
    return list(filter(lambda x: x.slug in slugs, manufacturers))


def _read_yaml_host_vars():
    global host_vars
    global devices

    host_vars = {}

    for host in devices:
        # we need get (instead of filter) in order to get ALL the keys i.e. config_context
        host = nb.dcim.devices.get(host.id)
        try:
            host_vars[host.name] = dict(_load_yaml_vars('host_vars/' + host.name), **host.config_context)
        except AttributeError:
            host_vars[host.name] = _load_yaml_vars('host_vars/' + host.name)
        #host_vars[host.name] = _load_yaml_vars('host_vars/' + host.name)


def _read_yaml_group_vars():
    global all_vars
    global manufacturer_vars
    global site_vars
    global role_vars

    global manufacturers
    global sites
    global roles
    global devices

    all_vars = {}
    manufacturer_vars = {}
    site_vars = {}
    role_vars = {}

    # Read all variables
    all_vars = _load_yaml_vars('group_vars/all')

    # Read manufacturer-specific variables
    for manufacturer in manufacturers:
        manufacturer_vars[manufacturer.slug] = _load_yaml_vars('group_vars/' + manufacturer.slug)

    # Read site-specific variables
    for site in sites:
        site_vars[site.slug] = _load_yaml_vars('group_vars/' + site.slug)

    # Read role-specific variables
    for role in roles:
        role_vars[role.slug] = _load_yaml_vars('group_vars/' + role.slug)


def get_inventory_list():
    global manufacturers
    global sites
    global roles
    global devices
    global host_vars

    inventory = {}

    # Return interesting manufacturers
    for manufacturer in manufacturers:
        inventory[manufacturer.slug] = {}
        inventory[manufacturer.slug]['vars'] = manufacturer_vars[manufacturer.slug]
        m_devices = _filter_devices(devices, manufacturer_slugs=manufacturer.slug)
        inventory[manufacturer.slug]['hosts'] = list(map(lambda x: x.name, m_devices))

    # Return all the sites
    for site in sites:
        inventory[site.slug] = {}
        inventory[site.slug]['vars'] = site_vars[site.slug]
        s_devices = _filter_devices(devices, site_slugs=site.slug)
        inventory[site.slug]['hosts'] = list(map(lambda x: x.name, s_devices))

    # Return interesting device roles
    for role in roles:
        inventory[role.slug] = {}
        inventory[role.slug]['vars'] = role_vars[role.slug]
        r_devices = _filter_devices(devices, role_slugs=role.slug)
        inventory[role.slug]['hosts'] = list(map(lambda x: x.name, r_devices))

    # Return rack-groups with devices belonging to both interesting roles and manufacturers and in rack belonging to that rack-group
    # This assumes that "cluster-x" is a rack group
    rack_groups = nb.dcim.rack_groups.all()
    racks = nb.dcim.racks.all()
    for rg in rack_groups:
        inventory[rg.slug] = {}
        inventory[rg.slug]['hosts'] = []
    for d in devices:
        r = _get_object_by_id(racks, d.rack.id)
        try:
            rg = _get_object_by_id(rack_groups, r.group.id)
            inventory[r.group.slug]['hosts'].append(d.name)
        except:
            pass

    # Return 'all' with devices belonging to both interesting roles and manufacturers
    inventory['all'] = {}
    inventory['all']['children'] = list(map(lambda x: x.slug, manufacturers + sites + roles))
    inventory['all']['hosts'] = list(map(lambda x: x.name, devices))
    inventory['all']['vars'] = all_vars

    # Return 'ungrouped' which will be empty
    inventory['ungrouped'] = {}
    inventory['ungrouped']['hosts'] = []

    # Return '_meta' which will include all hostvars
    inventory['_meta'] = {}
    inventory['_meta']['hostvars'] = host_vars

    return inventory


def get_inventory_host(host):
    global all_vars
    global manufacturer_vars
    global site_vars
    global host_vars
    global devices

    inventory_host = {}

    # This function doesn't guarantee that the returned host variables are
    # combined the same way as if using an static inventory

    try:
        # Return immediately if this is not a device 'managed' by us
        device = _get_device_by_name(devices, host)
        if device.device_type.manufacturer.slug not in MANUFACTURERS:
            return {}
        if device.device_role.slug not in DEVICE_ROLES:
            return {}

        # Assign 'all' variables
        inventory_host.update(all_vars)

        # Read manufacturer-specific variables
        inventory_host.update(manufacturer_vars[device.device_type.manufacturer.slug])

        # Read site-specific variables
        inventory_host.update(site_vars[device.site.slug])

        # Read host-specific variables
        inventory_host.update(host_vars[host])

        return inventory_host

    except Exception as ex:
        #template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        #message = template.format(type(ex).__name__, ex.args)
        #print(message)
        return {}


def main(argv):
    return_host = False
    host = ''
    return_list = False

    try:
        opts, args = getopt.getopt(argv, "lh:", ["list", "host="])
    except getopt.GetoptError:
        print('Syntax:')
        print('inventory.py --list')
        print('inventory.py --host')
        sys.exit(1)
    for opt, arg in opts:
        if opt in ('-h', '--host'):
            return_host = True
            host = arg
        elif opt in ('-l', '--list') and arg == '':
            return_list = True
        else:
            print('Syntax:')
            print('inventory.py --list')
            print('inventory.py --host')
            sys.exit(2)


    if (return_host and not return_list):
        _fetch_nb_endpoints(hostname=host)
        _read_yaml_group_vars()
        _read_yaml_host_vars()
        _print_inventory(get_inventory_host(host))

    elif (return_list and not return_host):
        _fetch_nb_endpoints()
        _read_yaml_group_vars()
        _read_yaml_host_vars()
        _print_inventory(get_inventory_list())

    else:
        sys.exit(4)


if __name__ == '__main__':
    main(sys.argv[1:])
