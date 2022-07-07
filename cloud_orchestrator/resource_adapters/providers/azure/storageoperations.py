from msrestazure.polling.arm_polling import OperationFailed
from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS
from azure.storage.fileshare import ShareServiceClient
from azure.data.tables import TableServiceClient
from azure.core.credentials import AzureNamedKeyCredential
from resource_adapters.utils.azure_clients import *

from util.core.app.logger import get_logger_func
LOG = get_logger_func(__file__)

def add_audit_log(session, task_id, source, event, trace, status):
    payload = {
        "task_id": task_id,
        "source": source,
        "event": event,
        "trace": trace,
        "status": status
    }
    LOG.debug("Insert audit logs:%s" % payload, {'task_id': task_id})
    insert_audit_log(payload, session_factory=session._session_factory)

def delete_storage_container(parameters, session, **kwargs):
    # Delete Storage container
    task_id = parameters.get('task_id')
    blob_service_client = get_blob_service_client(parameters)
    LOG.debug("Delete storage container:%s" % parameters, {'task_id': task_id})
    add_audit_log(session, task_id, "StorageOperation", "delete_storage_container",
                  "started", TASK_STATUS.COMPLETED)
    container_list = parameters.get("containers_list")
    exception_list = []
    for container in container_list:
        try:
            add_audit_log(session, task_id, "StorageOperation",
                          "delete_storage_container:%s" % container,
                          "started", TASK_STATUS.COMPLETED)
            blob_service_client.delete_container(container)
            add_audit_log(session, task_id, "StorageOperation",
                          "delete_storage_container:%s" % container,
                          "Success", TASK_STATUS.COMPLETED)
        except Exception as ex:
            exception_list.append({container: str(ex)})
    if exception_list:
        raise Exception("Failed to delete containers:%s" % exception_list)

def delete_storage_queue(parameters, session, **kwargs):
    # Delete Storage queue
    task_id = parameters.get('task_id')
    queue_service_client = get_queue_service_client(parameters)
    LOG.debug("Delete storage queue:%s" % parameters, {'task_id': task_id})
    add_audit_log(session, task_id, "StorageOperation", "delete_storage_queue",
                  "started", TASK_STATUS.COMPLETED)
    queue_list = parameters.get("queues")
    exception_list = []
    for queue in queue_list:
        try:
            add_audit_log(session, task_id, "StorageOperation",
                               "delete_storage_queue:%s" % queue,
                               "started", TASK_STATUS.COMPLETED)
            queue_service_client.delete_queue(queue)
            add_audit_log(session, task_id, "StorageOperation",
                          "delete_storage_queue:%s" % queue,
                          "Success", TASK_STATUS.COMPLETED)
        except Exception as ex:
            exception_list.append({queue: str(ex)})
    if exception_list:
        raise Exception("Failed to delete queue:%s" % exception_list)

def delete_datalake_storage(parameters, session, **kwargs):
    # Delete Data Lake Storage
    task_id = parameters.get('task_id')
    resource_group_name = parameters.get('resource_group_name')
    datalake_list = parameters.get("datalake_list")
    exception_list = []     
    datalake_client = get_datalake_client(parameters)

    LOG.debug("Delete DataLake Storage:%s" % parameters, {'task_id': task_id})
    add_audit_log(session, task_id, "StorageOperation", "delete_datalake_storage",
                  "started", TASK_STATUS.COMPLETED)

    for datalake_name in datalake_list:
        try:
            add_audit_log(session, task_id, "StorageOperation",
                        f"delete_datalake_storage:{datalake_name}",
                          "started", TASK_STATUS.COMPLETED)
            # Azure Cloud Operation                     
            datalake_client.accounts.delete(
                resource_group_name=resource_group_name, account_name=datalake_name)
            add_audit_log(session, task_id, "StorageOperation",
                        f"delete_datalake_storage:{datalake_name}",
                          "Success", TASK_STATUS.COMPLETED)
        except Exception as ex:
            exception_list.append({datalake_name: str(ex)})

    if exception_list:
        raise Exception("Failed to delete datalake:%s" % exception_list)

def delete_storage_account(parameters, session, **kwargs):
    # Delete Storage account
    task_id = parameters.get('task_id')
    storage_client = get_storage_client(parameters)
    LOG.debug("Delete storage account:%s" % parameters,
              {'task_id': task_id})
    add_audit_log(session, task_id, "StorageOperation", "delete_storage_account",
                  "started", TASK_STATUS.COMPLETED)
    account_name = parameters.get("storage_account_name")
    try:
        add_audit_log(session, task_id, "StorageOperation",
                      "delete_storage_account:%s" % account_name,
                      "started", TASK_STATUS.COMPLETED)
        storage_client.storage_accounts.delete(
            parameters.get('resource_group_name'), account_name)
        add_audit_log(session, task_id, "StorageOperation",
                           "delete_storage_account:%s" % account_name,
                           "Success", TASK_STATUS.COMPLETED)
    except Exception as ex:
            raise Exception("Failed to delete storage account%s" % str(ex))

def delete_storage_fileshare(parameters, session, **kwargs):
    # Delete Storage share
    task_id = parameters.get('task_id')
    account_name = parameters.get('storage_account_name')
    storage_client = get_storage_client(parameters)
    LOG.debug("Delete storage share:%s" % parameters, {'task_id': task_id})
    add_audit_log(session, task_id, "StorageOperation", "delete_storage_fileshare",
                  "started", TASK_STATUS.COMPLETED)
    share_list = parameters.get("file_shares")
    exception_list = []
    storage_keys = storage_client.storage_accounts.list_keys(
        parameters.get('resource_group_name'), account_name)
    storage_keys = {v.key_name: v.value for v in storage_keys.keys}
    secret_key = None
    for _, value in storage_keys.items():
        secret_key = value
        break
    share_client = ShareServiceClient(
        account_url="https://%s.file.core.windows.net" % account_name,
        credential=secret_key)
    for share in share_list:
        try:
            add_audit_log(session, task_id, "StorageOperation",
                          "delete_storage_fileshare:%s" % share,
                          "started", TASK_STATUS.COMPLETED)
            share_client.delete_share(share, delete_snapshots=True)
            add_audit_log(session, task_id, "StorageOperation",
                          "delete_storage_fileshare:%s" % share,
                          "Success", TASK_STATUS.COMPLETED)
        except Exception as ex:
            exception_list.append({share: str(ex)})
    if exception_list:
        raise Exception("Failed to delete share:%s" % exception_list)

def delete_storage_table(parameters, session, **kwargs):   
    # Delete table from storage account
    task_id = parameters.get('task_id')
    account_name = parameters.get('storage_account_name')    
    LOG.debug("Delete table from storage account:%s" % parameters, {'task_id': task_id})
    add_audit_log(session, task_id, "StorageOperation", "delete_table_from_storage", 
                  "started", TASK_STATUS.COMPLETED)
    tables_list = parameters.get("table_name")
    exception_list = []
    storage_client = get_storage_client(parameters)
    storage_keys = storage_client.storage_accounts.list_keys(
            parameters.get('resource_group_name'), account_name)
    storage_keys = {v.key_name: v.value for v in storage_keys.keys}
    secret_key = None
    for _, value in storage_keys.items():
        secret_key = value
        break
    credential = AzureNamedKeyCredential(account_name, secret_key)
    table_service = TableServiceClient(endpoint="https://%s.table.core.windows.net" %account_name, 
                                      credential=credential)
    try:        
        for table in tables_list:
            add_audit_log(session, task_id, "StorageOperation", 
                      "delete_table_from_storage:%s" %table,
                      "started", TASK_STATUS.COMPLETED)
            table_service.delete_table(table)
            add_audit_log(session, task_id, "StorageOperation", 
                           "delete_table_from_storage:%s" %table,
                           "Success", TASK_STATUS.COMPLETED)
        
    except Exception as ex:
        raise Exception("Failed to delete table from storage account : %s" % str(ex))   