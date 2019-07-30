# OS_OSM_deployer
Automatize the entire process from management network creation in OpenStack till deploying a Network Service from OSM

## Requirements

Python library requirements:

- python-openstack
- python-neutronclient
- osmclient

Install dependencies and mandatory Python libraries:
```
apt install python-pip libcurl4-gnutls-dev libgnutls-dev
pip install python-openstack
pip install python-neutronclient
pip install python-magic
pip install git+https://osm.etsi.org/gerrit/osm/osmclient
```

## Usage Instructions

```
cd ~ && git clone https://github.com/herlesupreeth/OS_OSM_deployer
cd OS_OSM_deployer
python deploy.py --help
Usage: deploy.py [OPTIONS]

Options:
  --osm_host TEXT              IP of OSM server  [required]
  --osm_user TEXT              OSM user  [required]
  --osm_password TEXT          OSM password  [required]
  --osm_project TEXT           OSM project  [required]
  --ns_name TEXT               Name of the Network Service instance
                               [required]
  --nsd_name TEXT              Name of the Network Service Descriptor to use
                               [required]
  --vim_account TEXT           Name of the VIM account to use for deployment
                               [required]
  --ns_config_file TEXT        Network Service configuration file
  --os_ctrl_host TEXT          IP of OpenStack Controller  [required]
  --os_user TEXT               OpenStack user  [required]
  --os_password TEXT           OpenStack password  [required]
  --os_project TEXT            OpenStack project/tenant  [required]
  --os_project_domain_id TEXT  OpenStack project domain id
  --os_user_domain_id TEXT     OpenStack user domain id
  --help                       Show this message and exit.
```

