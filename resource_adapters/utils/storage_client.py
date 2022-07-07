import isi_sdk_8_2_1 as isilon_sdk

def get_dell_isilon_client(parameters):
    configuration = isilon_sdk.Configuration()
    configuration.host = parameters.get('host')
    configuration.username = parameters.get('username')
    configuration.password = parameters.get('password')
    configuration.verify_ssl = parameters.get('verify_ssl')
    return isilon_sdk.ApiClient(configuration)

