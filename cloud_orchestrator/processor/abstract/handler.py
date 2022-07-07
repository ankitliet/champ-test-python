'''
: `engine.py` file contains the abstarct engine versions[`#LINEAR | #THREADED | ASYNC | #MULTIPROCESS`]
: An adroit is responsible for atomic process and have control over its domain. The domain includes all
  the sockets, datastructures, pollers, connections etc.
  Each adroit can run independently and serves the roles attached to it for long period of time.


: External Imports:
    : abc:
        : ABC
        : ABCMeta
        : abstractmethod

'''
from abc import (ABC,
                 ABCMeta,
                 abstractmethod)



    
class AbstractHandler(metaclass=ABCMeta):
    '''
    : `AsyncAbstractAdroit` class is the async version of the adroit abstract class that 
      drives the async adroits and its required methods.
    '''
    def __init__(self, **kwargs):
        ...