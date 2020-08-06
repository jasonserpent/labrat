
<!-- vim-markdown-toc GitLab -->

* [Installation](#installation)
* [Netbox](#netbox)
* [Ansible](#ansible)
  * [ansible.cfg](#ansiblecfg)
  * [Inventory](#inventory)
  * [Group vars](#group-vars)
* [Usage](#usage)

<!-- vim-markdown-toc -->


# Installation
```
$ pip3 install -r requirements3.txt
```

# Netbox
Access to your account settings and generate a token.

# Ansible
## ansible.cfg
Edit ansible.cfg and update the library path to wherever your napalm_ansible packages were installed on your local machine.
```cfg
library = ./lib:../.direnv/python-3.7.3/lib/python3.7/site-packages/napalm_ansible
```

## Inventory
Edit `inventory/netbox_inventory.py` and use your own Netbox token:
```python
nb = pynetbox.api(NETBOX_URL, token='sometokengeneratedonnetbox1234567890')
```


## Group vars
Edit or create `inventory/group_vars/local_vars`
```yaml
---
ansible_python_interpreter: /path/to/bin/python3
netbox_token: sometokengeneratedonnetbox1234567890
ansible_user: someusername
ansible_password: somesecretpassword
```
# Usage
```
$ cd ansible
$ ansible-playbook backup.yaml
```
