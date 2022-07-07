'''
# TODO 
1. COMMENTS and TYPING HINTS
'''

from dependency_injector import containers, providers, errors

from abstract.engine import AbstractEngine




class EngineFactoryProvider(providers.Factory):
    provided_type = AbstractEngine
    