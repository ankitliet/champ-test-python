import gflags
from enum import Enum


class TASK_STATUS():
    QUEUED = "IN_QUEUE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "SUCCESS"
    FAILED = "FAILED"
    NOT_INITIATED = "NOT INITIATED"

class MAINTAINANCE_MODE(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

FLAGS = gflags.FLAGS

gflags.DEFINE_string("log_location",
                     "/var/logs",
                     "path where default logging should be done.")

gflags.DEFINE_boolean("separate_log_files",
                      True,
                      "Separate log file required or not."
                      "Default True for separate log file")

gflags.DEFINE_boolean("enable_file_compression",
                      True,
                      "Compression of log files required or not."
                      "Should be True for multiprocess Service")

gflags.DEFINE_string("log_file",
                     "default.log",
                     "Default log file name.")

gflags.DEFINE_integer("log_file_size",
                      10 * 1024 * 1024,
                      "Default log file size (10mb).")

gflags.DEFINE_integer("log_backup_count",
                      5,
                      "Number of log files to roll.")

gflags.DEFINE_string("log_level",
                     "INFO",
                     "Default log level.")

gflags.DEFINE_string("logger_name",
                     "default_logger",
                     "Default logger name.")

gflags.DEFINE_string("log_format",
                     "%(asctime)s,%(msecs)03d %(levelname)s %(process)d %(task_id)s:"
                     "%(filename)s:%(funcName)s: %(lineno)d - %(message)s",
                     "Default log message format.")