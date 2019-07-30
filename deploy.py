# BSD 2-Clause License

# Copyright (c) 2019, Supreeth Herle
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import click
import time
from random import randint
import json

from osmclient import client
from osmclient.common.exceptions import ClientException

from keystoneauth1 import identity
from keystoneauth1 import session
from neutronclient.v2_0 import client as neutclient
from neutronclient.common import exceptions as neutron_exceptions

@click.command()
@click.option('--osm_host',
			required=True,
			help='IP of OSM server')
@click.option('--osm_user',
			required=True,
			help='OSM user')
@click.option('--osm_password',
			prompt=True, hide_input=True,
			required=True,
			help='OSM password')
@click.option('--osm_project',
			required=True,
			help='OSM project')
@click.option('--ns_name',
			required=True,
			help='Name of the Network Service instance')
@click.option('--nsd_name',
			required=True,
			help='Name of the Network Service Descriptor to use')
@click.option('--vim_account',
			required=True,
			help='Name of the VIM account to use for deployment')
@click.option('--ns_config_file',
			default=None,
			help='Network Service configuration file')
@click.option('--os_ctrl_host',
			required=True,
			help='IP of OpenStack Controller')
@click.option('--os_user',
			required=True,
			help='OpenStack user')
@click.option('--os_password',
			prompt=True, hide_input=True,
			required=True,
			help='OpenStack password')
@click.option('--os_project',
			required=True,
			help='OpenStack project/tenant')
@click.option('--os_project_domain_id',
			default='default',
			help='OpenStack project domain id')
@click.option('--os_user_domain_id',
			default='default',
			help='OpenStack user domain id')
def start(osm_host,
		  osm_user,
		  osm_password,
		  osm_project,
		  ns_name,
		  nsd_name,
		  vim_account,
		  ns_config_file,
		  os_ctrl_host,
		  os_user,
		  os_password,
		  os_project,
		  os_project_domain_id,
		  os_user_domain_id):
	# OSM arguments
	osm_kwargs={}
	osm_kwargs['osm_host'] = osm_host
	osm_kwargs['osm_user'] = osm_user
	osm_kwargs['osm_password'] = osm_password
	osm_kwargs['osm_project'] = osm_project
	osm_kwargs['ns_name'] = ns_name
	osm_kwargs['nsd_name'] = nsd_name
	osm_kwargs['vim_account'] = vim_account
	osm_kwargs['ns_config_file'] = ns_config_file

	# OpenStack arguments
	os_kwargs={}
	os_kwargs['auth_url'] = 'http://' + os_ctrl_host + '/identity'
	os_kwargs['os_user'] = os_user
	os_kwargs['os_password'] = os_password
	os_kwargs['os_project'] = os_project
	os_kwargs['os_project_domain_id'] = os_project_domain_id
	os_kwargs['os_user_domain_id'] = os_user_domain_id

	# OSM client instance
	osm_cl = init_osm_client(osm_kwargs)
	if not osm_cl:
		print("OSM client error")
		exit(1)

	# deploy_ns(osm_cl, osm_kwargs)
	# get_ns(osm_cl, osm_kwargs['ns_name'])
	# del_ns(osm_cl, osm_kwargs['ns_name'])

	# OpenStack Session Instance
	os_session = get_os_session(os_kwargs)
	if not os_session:
		print("OpenStack Session could not be established")
		exit(1)
	# Get the neutron context
	neutron = None
	try:
		neutron = neutclient.Client(session=os_session)
	except neutron_exceptions as e:
		print(e.message)
		exit(1)

	# Create the management network in OpenStack
	create_mgmt_net(neutron, os_kwargs)
	# Deploy the Network Service from OSM
	deploy_ns(osm_cl, osm_kwargs)
	# get_vim_security_groups(osm_cl, osm_kwargs['vim_account'])

def print_response(resp):
	print(json.dumps(resp, indent=2))

# Create an OpenStack Session to execute OpenStack commands
def get_os_session(os_params):
	s = None
	try:
		auth = identity.Password(auth_url=os_params['auth_url'],
						 username=os_params['os_user'],
						 password=os_params['os_password'],
						 project_name=os_params['os_project'],
						 project_domain_id=os_params['os_project_domain_id'],
						 user_domain_id=os_params['os_user_domain_id'])
		s = session.Session(auth=auth)
	except Exception as e:
		print(e)
		exit(1)

	return s

def create_mgmt_net(neutron, os_params):
	try:
		# Create management net if it does not exists
		networks = neutron.list_networks(name=os_params['os_project'] + '_mgmt_net')['networks']
		if len(networks) == 0:
			net_req = {
				'network': {
					'name': os_params['os_project'] + '_mgmt_net',
					'admin_state_up': True
				}
			}
			net_resp = neutron.create_network(body=net_req)
			network_id = net_resp['network']['id']
			print('Network %s created' % network_id)
		else:
			network_id = networks[0]['id']
			print('Network %s exists' % network_id)

		# Create management sub-net if it does not exists
		subnets = neutron.list_subnets(name=os_params['os_project'] + '_mgmt_subnet')['subnets']
		if len(subnets) == 0:
			subnet_req = {
				'subnets': [
						{
							'cidr': '192.168.' + str(randint(0, 255)) + '.0/24',
							'ip_version': 4,
							'name': os_params['os_project'] + '_mgmt_subnet',
							'network_id': network_id
						}
					]
			}
			subnet_resp = neutron.create_subnet(body=subnet_req)
			subnet_id = subnet_resp['subnets'][0]['id']
			print('Sub-Net %s created' % subnet_id)
		else:
			subnet_id = subnets[0]['id']
			print('Sub-Net %s exists' % subnet_id)

		# Create router for external connectivity to management net if it does not exist
		routers = neutron.list_routers(name=os_params['os_project'] + '_router')['routers']
		if len(routers) == 0:
			router_req = {
				'router': {
					'name': os_params['os_project'] + '_router',
					'admin_state_up': True
				}
			}
			router_resp = neutron.create_router(router_req)
			router_id = router_resp['router']['id']
			print('Router %s created' % router_id)
		else:
			router_id = routers[0]['id']
			print('Router %s exists' % router_id)

		# Add interface to router if it does not exist
		search_port = {
			'device_owner': 'network:router_interface',
			'network_id': network_id
		}
		ports = neutron.list_ports(**search_port)['ports']
		if len(ports) == 0:
			interface_req = {
				'subnet_id': subnet_id
			}
			interface_resp = neutron.add_interface_router(router_id, body=interface_req)
			print('Added interface to router')

		# Add gateway to router if it does not exist
		search_publicnets = {
			'router:external': True
		}
		public_networks = neutron.list_networks(**search_publicnets)['networks']
		public_net_id = public_networks[0]['id']

		pub_router = neutron.show_router(router_id)['router']
		if not pub_router['external_gateway_info']:
			gateway_req = {
				'network_id': public_net_id
			}
			gateway_resp = neutron.add_gateway_router(router_id, body=gateway_req)

		print('Management Network: ' + os_params['os_project'] + '_mgmt_net' + ' is ready!!')
	except neutron_exceptions as e:
		print(e.message)
		exit(1)

# Create an instance of OSM client to execute OSM client commands
def init_osm_client(osm_params):
	c = None
	try:
		c = client.Client(host=osm_params['osm_host'],
						 sol005=True,
						 user=osm_params['osm_user'],
						 password=osm_params['osm_password'],
						 project=osm_params['osm_project'],
						 **osm_params)
	except Exception as e:
		print(e)
		exit(1)

	return c

# Deploy a Network Service
def deploy_ns(osm_client, osm_params):
	# Check whether a Network Service with same name exists
	# Prohibit usage of same NS names
	try:
		ns_list = osm_client.ns.list(filter='name=' + osm_params['ns_name'])
	except ClientException as inst:
		print(inst.message)
		exit(1)

	if len(ns_list) > 0:
		print("Network Service by this name already exists. " +
			  "Please provide a unique NS name")
		exit(1)

	try:
		config = None
		if osm_params['ns_config_file']:
			with open(osm_params['ns_config_file'], 'r') as cf:
				config = cf.read()
		osm_client.ns.create(osm_params['nsd_name'],
							 osm_params['ns_name'],
							 config=config,
							 ssh_keys=None,
							 account=osm_params['vim_account'])
	except ClientException as inst:
		print(inst.message)
		exit(1)

	# Poll here for status of the deployed NS and provide the status of deployment
	while True:
		time.sleep(1)
		ns = get_ns(osm_client, osm_params['ns_name'])
		print(ns['detailed-status'] + ': Operational State: ' + ns['operational-status'])
		if ns['operational-status'] != 'init' and ns['config-status'] != 'init':
			break

# Get deployed Network Service details
def get_ns(osm_client, ns_name):
	try:
		ns = osm_client.ns.get(ns_name)
	except ClientException as inst:
		print((inst.message))
		exit(1)

	return ns

def get_vim_security_groups(osm_client, vim_account):
	try:
		vim = osm_client.vim.get(vim_account)
	except ClientException as inst:
		print((inst.message))
		exit(1)

	# return ns
	print(json.dumps(vim, indent=2))

# Delete Network Service
def del_ns(osm_client, ns_name):
	try:
		osm_client.ns.delete(ns_name)
	except ClientException as inst:
		print((inst.message))
		exit(1)

if __name__ == '__main__':
	start()

