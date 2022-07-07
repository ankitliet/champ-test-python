
#EXTERNAL IMPORTS
import os
import sys

#SETTING CONFIGS
release = os.environ.get('RELEASE_ENV')

#IMPORTING CONFIGS
import importlib
config = getattr(importlib.import_module(f'.{release}', package='core.settings'), 'settings')



#PROXY CLASS
class configurations:
    def __getattr__(self, name):
        return getattr(config, name)


sys.modules[__name__] = configurations()
