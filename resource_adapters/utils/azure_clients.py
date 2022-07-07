import json
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
from azure.mgmt.resource import ResourceManagementClient

############ Resource Management Client ########
def get_resourcegroup_client(parameters):
    tenant_id = parameters.get('azure_tenant_id')
    client_id = parameters.get('azure_client_id')
    secret = parameters.get('azure_client_secret')
    subscription_id = parameters.get('azure_subscription_id')

    token_credential = ClientSecretCredential(
        tenant_id, client_id, secret)
    resourcegroup_client = ResourceManagementClient(token_credential, subscription_id)
    return resourcegroup_client

########### Resource Management Client End #####
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
