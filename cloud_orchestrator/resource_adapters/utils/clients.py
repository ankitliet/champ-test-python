import json
import openstack
from azure.identity import ClientSecretCredential
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.privatedns import PrivateDnsManagementClient
from azure.mgmt.dns import DnsManagementClient
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueServiceClient
from azure.mgmt.datalake.store import DataLakeStoreAccountManagementClient
from pyVim.connect import SmartConnect, Disconnect
from atexit import register

# GCP
from google.oauth2 import service_account
from google.cloud import compute_v1
from google.cloud.compute import AddressesClient, FirewallsClient,\
    NetworksClient, SubnetworksClient
from google.cloud.compute import ImagesClient

def get_compute_client(parameters):
    tenant_id = parameters.get('azure_tenant_id')
    client_id = parameters.get('azure_client_id')
    secret = parameters.get('azure_client_secret')
    subscription_id = parameters.get('azure_subscription_id')

    token_credential = ClientSecretCredential(
        tenant_id, client_id, secret)
    compute_client = ComputeManagementClient(token_credential,
                                             subscription_id)
    return compute_client


def get_network_client(parameters):
    tenant_id = parameters.get('azure_tenant_id')
    client_id = parameters.get('azure_client_id')
    secret = parameters.get('azure_client_secret')
    subscription_id = parameters.get('azure_subscription_id')

    token_credential = ClientSecretCredential(
        tenant_id, client_id, secret)
    network_client = NetworkManagementClient(token_credential,
                                             subscription_id)
    return network_client


def get_dns_client(parameters):
    tenant_id = parameters.get('azure_tenant_id')
    client_id = parameters.get('azure_client_id')
    secret = parameters.get('azure_client_secret')
    subscription_id = parameters.get('azure_subscription_id')

    token_credential = ClientSecretCredential(
        tenant_id, client_id, secret)
    dns_client = PrivateDnsManagementClient(token_credential,
                                            subscription_id)
    return dns_client


def get_dns_ops_client(parameters):
    tenant_id = parameters.get('azure_tenant_id')
    client_id = parameters.get('azure_client_id')
    secret = parameters.get('azure_client_secret')
    subscription_id = parameters.get('azure_subscription_id')

    token_credential = ClientSecretCredential(
        tenant_id, client_id, secret)
    dns_ops_client = DnsManagementClient(token_credential,
                                            subscription_id)
    return dns_ops_client



def get_blob_service_client(parameters):
    tenant_id = parameters.get('azure_tenant_id')
    client_id = parameters.get('azure_client_id')
    secret = parameters.get('azure_client_secret')
    account_name = parameters.get('storage_account_name')
    token_credential = ClientSecretCredential(
        tenant_id, client_id, secret)
    blob_service_client = BlobServiceClient(
        account_url="https://%s.blob.core.windows.net" % account_name,
        credential=token_credential)
    return blob_service_client


def get_queue_service_client(parameters):
    tenant_id = parameters.get('azure_tenant_id')
    client_id = parameters.get('azure_client_id')
    secret = parameters.get('azure_client_secret')
    account_name = parameters.get('storage_account_name')
    token_credential = ClientSecretCredential(
        tenant_id, client_id, secret)
    queue_service_client = QueueServiceClient(
        account_url="https://%s.queue.core.windows.net" % account_name,
        credential=token_credential)
    return queue_service_client

def get_datalake_client(parameters):
    tenant_id = parameters.get('azure_tenant_id')
    client_id = parameters.get('azure_client_id')
    secret = parameters.get('azure_client_secret')
    subscription_id = parameters.get('azure_subscription_id')
    credentials = ServicePrincipalCredentials(
        client_id=client_id,
        secret=secret,
        tenant=tenant_id)

    datalake_client = DataLakeStoreAccountManagementClient(credentials,
                                                           subscription_id)
    return datalake_client

def get_storage_client(parameters):
    tenant_id = parameters.get('azure_tenant_id')
    client_id = parameters.get('azure_client_id')
    secret = parameters.get('azure_client_secret')
    subscription_id = parameters.get('azure_subscription_id')

    token_credential = ClientSecretCredential(
        tenant_id, client_id, secret)
    storage_client = StorageManagementClient(token_credential,
                                             subscription_id)
    return storage_client

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

def get_vmware_client(parameters):
    vmware_server = parameters.get('vmware_server')
    vmware_username = parameters.get('vmware_username')
    vmware_password = parameters.get('vmware_password')
    ssl_cert_validation = parameters.get('ssl_cert_validation')

    vmware_client = None
    if ssl_cert_validation:
        vmware_client = SmartConnect(
            host=vmware_server, user=vmware_username, pwd=vmware_password)
    else:
        vmware_client = SmartConnect(host=vmware_server, user=vmware_username,
                                     pwd=vmware_password, disableSslCertValidation=True)
        register(Disconnect, vmware_client)

    return vmware_client


def get_openstack_client(parameters):
    auth_url = parameters.get('auth_url')
    project_name = parameters.get('tenant_name')
    password = parameters.get('password')
    username = parameters.get('user_name')
    region_name = parameters.get('region')
    project_domain_name = parameters.get('project_domain_name', 'default')
    user_domain_name = parameters.get('user_domain_name', 'default')
    client = openstack.connect(auth_url=auth_url, project_name=project_name,
                               username=username, password=password,
                               region_name=region_name, verify=False,
                               project_domain_name=project_domain_name,
                               user_domain_name=project_domain_name)
    return client
