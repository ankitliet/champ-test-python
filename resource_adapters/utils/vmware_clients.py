from pyVim.connect import SmartConnect, Disconnect
from atexit import register
import json



def get_vmware_client(parameters):
    vsphere_server = parameters.get('vsphere_server')
    vsphere_user = parameters.get('vsphere_user')
    vsphere_password = parameters.get('vsphere_password')
    ssl_cert_validation = parameters.get('ssl_cert_validation')

    vmware_client = None
    if ssl_cert_validation:
        vmware_client = SmartConnect(
            host=vsphere_server, user=vsphere_user, pwd=vsphere_password)
    else:
        vmware_client = SmartConnect(host=vsphere_server, user=vsphere_user,
                                     pwd=vsphere_password, disableSslCertValidation=True)
        register(Disconnect, vmware_client)

    return vmware_client
