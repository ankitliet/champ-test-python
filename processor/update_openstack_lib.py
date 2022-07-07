import site
import os

paths = site.getsitepackages()
for p in paths:
    try:
        path = os.path.join(p,'openstack/config')
        path_loader = os.path.join(path,'loader.py')
        upd_path = '/usr/src/app/hcmp_orchestrator_processor'
        #print('file loader.py at: ' + path_loader)
        os.chmod(path_loader, 0o777)
        with open(path_loader, 'r') as file:
            filedata = file.read()
        filedata = filedata.replace('os.getcwd()', str("'" + str(upd_path) + "'"))
        with open(path_loader, 'w') as file:
            file.write(filedata)
        print('Successfully Updated loader.py file at {}'.format(path_loader))

    except Exception as ex:
        print('Couldn\'t update Openstack library for path({})'.format(p,str(ex)))
