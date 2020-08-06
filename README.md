
<!-- vim-markdown-toc GitLab -->

* [Installation](#installation)
* [Ansible](#ansible)
  * [Inventory](#inventory)

<!-- vim-markdown-toc -->



# Installation

`pip3 install -r requirements3.txt`

# Ansible

## Inventory
Edit `inventory/group_vars/local_vars`

```yaml
---
ansible_python_interpreter: ../.direnv/python-3.7.3/bin/python3
netbox_token: cccccccccccccccccccccccccccccccccccccccc
ansible_user: pppppppp
ansible_password: pppppppppppppppp
```

