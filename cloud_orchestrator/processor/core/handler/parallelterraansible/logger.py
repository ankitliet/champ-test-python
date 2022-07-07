import logging
import os



class getlogger:
    
    def __init__(self, name=None):
        self.logger = self.createlogger(name=name)
        
    def createlogger(self, name):
        if getattr(self, '_name', None) is not None:
            self._name = '_'.join([self._name, name])
        else:
            self._name = name
        logger = logging.getLogger(self._name)
        logger.setLevel(getattr(logging, os.environ.get('LOGLEVEL', 'DEBUG')))
        return logger
    
    def getlogger(self, name=None):
        self.logger = self.createlogger(name=name)
        return self
    
    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)
        
    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)
        
    def exception(self, msg, *args, **kwargs):
        self.logger.exception(msg, *args, **kwargs)
        
    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)
        
    def error(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)