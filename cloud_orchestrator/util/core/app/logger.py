# #!/usr/bin/env python

import gzip
import logging
import sys
import os
import os.path
import traceback
import time

import gflags

from logging.handlers import RotatingFileHandler


LOG_LEVELS = {
  "DEBUG": logging.DEBUG,
  "INFO": logging.INFO,
  "WARNING": logging.WARNING,
  "ERROR": logging.ERROR,
  "CRITICAL": logging.CRITICAL
}

FLAGS = gflags.FLAGS
gflags.FLAGS(sys.argv)


def get_logger_func(name=None):
  try:
    return getFileLogger(name=name)
  except Exception as ex:
    raise ex

class TaskIdFormatter(logging.Formatter):
  """
  Custom Formatter which append transaction ID in log message.
  """
  def format(self, record):
    record.task_id = "N/A"
    if isinstance(record.msg, str):
        record.msg = record.msg.replace("%", "&")
    if record.args:
        record.task_id = record.args.get("task_id", "N/A")
    return super().format(record)

class GzipRotatingFileHandler(RotatingFileHandler):
  """
   Class for compressing the Log files while rotating.
   Overriden Methods: __init__ and doRollOver
  """
  def __init__(self, filename, **kws):
    backupCount = kws.get('backupCount', 0)
    self.backup_count = backupCount
    RotatingFileHandler.__init__(self, filename, **kws)

  def doArchive(self, old_log):
    """
     This method perform archival of the log file.
     Returns: None
    """
    try:
      with open(old_log) as log:
        with gzip.open(old_log + '.gz', 'wb') as comp_log:
          comp_log.writelines(log)
      if os.path.isfile(old_log):
        os.remove(old_log)
    except Exception as e:
      print(traceback.format_exc())

  def doRollover(self):
    """
     This method rolls over the log file when reaches to maxBytes.
     Returns: None
    """
    if self.stream:
      self.stream.close()
      self.stream = None
    # Roll over the log files only when size of .log file exceeds
    # maxBytes value
    try:
      baseFileSize = os.stat(self.baseFilename).st_size
      if self.backup_count > 0 and self.maxBytes <= baseFileSize:
        for i in range(self.backup_count - 1, 0, -1):
          sfn = "%s.%d.gz" % (self.baseFilename, i)
          dfn = "%s.%d.gz" % (self.baseFilename, i + 1)
          if os.path.exists(sfn):
            if os.path.exists(dfn):
              os.remove(dfn)
            os.rename(sfn, dfn)
        dfn = self.baseFilename + ".1"
        if os.path.exists(dfn):
          os.remove(dfn)
        if os.path.exists(self.baseFilename):
          os.rename(self.baseFilename, dfn)
          self.doArchive(dfn)
    except Exception as e:
      print(traceback.format_exc())


class INFOFilter(logging.Filter):
  def filter(self, record):
    if record.levelname == "INFO" or record.levelname == "WARNING" :
      return 1
    else :
      return 0

class ERRORFilter(logging.Filter):
  def filter(self, record):
    if record.levelname == "ERROR" or record.levelname == "CRITICAL" :
      return 1
    else :
      return 0

class DEBUGFilter(logging.Filter):
  def filter(self, record):
    if record.levelname == "DEBUG" :
      return 1
    else :
      return 0

def getFileLogger(name=None, location=None, logfile=None, loglevel=None,
  separate_log_files=None):
  """
  This method returns the logger instance.
  """
  print("getFileLogger:%s" % name)
  try:
    if not name:
      name = FLAGS.logger_name

    if not location:
      location = FLAGS.log_location

    if not logfile:
      logfile = FLAGS.log_file

    if not loglevel:
      loglevel = FLAGS.log_level

    if location and not os.path.exists(location):
      os.makedirs(location)

    if separate_log_files is None:
      separate_log_files = FLAGS.separate_log_files

    if not separate_log_files:
      handlers_list = [loglevel]
    else:
      handlers_list = ["ERROR", "INFO", "DEBUG"]

    print("getFileLogger:%s:%s:%s:%s:%s" %
          (name, location, logfile, loglevel, handlers_list))

    logger = logging.getLogger(name)
    # Setting the logger level to lowest and
    # it will be overriden at handlers level
    logger.setLevel("DEBUG")
    setHandlers(logger, location, logfile, loglevel, handlers_list,
                separate_log_files)
  except Exception as e:
    print(traceback.format_exc())
  return logger


def setHandlers(logger, location, logfile, loglevel, handlers_list,
  separate_log_files):
  """
  This functions adds handlers to the logger
  based on the flag to seperate log files
  or to write to a single log file
  """
  filepath = os.path.join(location, logfile)
  for handler_name in handlers_list :
    if is_handler_required(logger, handler_name):
      if separate_log_files :
        filepath = os.path.join(location, logfile+".%s" % handler_name)
      if FLAGS.enable_file_compression:
        log_handler =  GzipRotatingFileHandler(filepath,
                                               maxBytes=FLAGS.log_file_size,
                                               backupCount=FLAGS.log_backup_count)
      else:
        log_handler = RotatingFileHandler(filepath,
                                          maxBytes=FLAGS.log_file_size,
                                          backupCount=FLAGS.log_backup_count)

      # Rotating Log File Handler, default max file size of 10MB
      log_handler.set_name(handler_name)
      log_format = FLAGS.log_format
      formatter = TaskIdFormatter(log_format)
      formatter.converter = time.gmtime
      log_handler.setFormatter(formatter)
      log_handler.setLevel(loglevel)
      stream_handler = logging.StreamHandler(sys.stdout)
      stream_handler.setFormatter(formatter)
      stream_handler.setLevel(loglevel)
      if separate_log_files :
        if handler_name == "ERROR":
          log_handler.addFilter(ERRORFilter())
          stream_handler.addFilter(ERRORFilter())
        elif handler_name == "INFO":
          log_handler.addFilter(INFOFilter())
          stream_handler.addFilter(INFOFilter())
        else:
          log_handler.addFilter(DEBUGFilter())
          stream_handler.addFilter(DEBUGFilter())
      logger.addHandler(log_handler)
      logger.addHandler(stream_handler)

def is_handler_required(logger, handler_name):
  """
  This method is used to check if logger already has
  RotatingFileHandler.
  Returns: False if RotatingFIleHandler is available
           else True.
  """
  if logger.hasHandlers():
    for handler in logger.handlers:
      if handler.get_name() == handler_name :
        return False
  return True
