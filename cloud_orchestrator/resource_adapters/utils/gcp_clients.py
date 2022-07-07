import json
from google.oauth2 import service_account
from google.cloud import compute_v1
from google.cloud.compute import AddressesClient, FirewallsClient,\
    NetworksClient, SubnetworksClient
from google.cloud.compute import ImagesClient


def get_gcp_instance_client(parameters):
    cred = parameters.get('credentials')
    if isinstance(cred, str):
        cred = json.loads(cred)
    credentials = service_account.Credentials.from_service_account_info(
        cred)
    instance_client = compute_v1.InstancesClient(credentials=credentials)
    return instance_client

def get_gcp_op_client(parameters):
    cred = parameters.get('credentials')
    if isinstance(cred, str):
        cred = json.loads(cred)
    credentials = service_account.Credentials.from_service_account_info(
        cred)
    op_client = compute_v1.ZoneOperationsClient(credentials=credentials)
    return op_client

def get_gcp_disk_client(parameters):
    cred = parameters.get('credentials')
    if isinstance(cred, str):
        cred = json.loads(cred)
    credentials = service_account.Credentials.from_service_account_info(
        cred)
    disk_client = compute_v1.DisksClient(credentials=credentials)
    return disk_client

def get_gcp_network_client(parameters):
    cred = parameters.get('credentials')
    if isinstance(cred, str):
        cred = json.loads(cred)
    credentials = service_account.Credentials.from_service_account_info(
        cred)
    network_client = NetworksClient(credentials=credentials)
    return network_client

def get_gcp_address_client(parameters):
    cred = parameters.get('credentials')
    if isinstance(cred, str):
        cred = json.loads(cred)
    credentials = service_account.Credentials.from_service_account_info(
        cred)
    address_client = AddressesClient(credentials=credentials)
    return address_client

def get_gcp_subnet_client(parameters):
    cred = parameters.get('credentials')
    if isinstance(cred, str):
        cred = json.loads(cred)
    credentials = service_account.Credentials.from_service_account_info(
        cred)
    subnet_client = SubnetworksClient(credentials=credentials)
    return subnet_client

def get_gcp_firewall_client(parameters):
    cred = parameters.get('credentials')
    if isinstance(cred, str):
        cred = json.loads(cred)
    credentials = service_account.Credentials.from_service_account_info(
        cred)
    firewall_client = FirewallsClient(credentials=credentials)
    return firewall_client

def get_gcp_wait_client_global(parameters):
    cred = parameters.get('credentials')
    if isinstance(cred, str):
        cred = json.loads(cred)
    credentials = service_account.Credentials.from_service_account_info(
        cred)
    wait_client = compute_v1.GlobalOperationsClient(credentials=credentials)
    return wait_client

def get_gcp_wait_client_regional(parameters):
    cred = parameters.get('credentials')
    if isinstance(cred, str):
        cred = json.loads(cred)
    credentials = service_account.Credentials.from_service_account_info(
        cred)
    wait_client = compute_v1.RegionOperationsClient(credentials=credentials)
    return wait_client

def get_gcp_image_client(parameters):
    cred = parameters.get('credentials')
    if isinstance(cred, str):
        cred = json.loads(cred)
    credentials = service_account.Credentials.from_service_account_info(
        cred)
    image_client = ImagesClient(credentials=credentials)
    return image_client
