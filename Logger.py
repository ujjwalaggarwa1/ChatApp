'''
A striped down logger from one of my previous projects
'''

import logging
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from queue import Queue
import os


_log_queue = Queue(-1)
FILE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | line:%(lineno)d | %(message)s"


def setup_logging(file:str="app", log_dir:str="logs", backup_count:int=9):
    """
    Set up the background listener.\n
    Add this to the start of the main app entry point.

    Args:
        file(str): The name of the log file.
        log_dir(str): The name of the folder in which logs will be stored.
        backup_count: Number of backup log files.
    """

    # Create the logs directory at the project root
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_filepath = os.path.join(log_dir, f"{file}.log")

    file_handler = RotatingFileHandler(log_filepath, maxBytes=10**6, backupCount=backup_count)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(FILE_FORMAT))

    # The listener runs in the background and processes the queue
    listener = QueueListener(_log_queue, file_handler, respect_handler_level=True)
    listener.start()
    return listener

def get_module_logger(name:str = __name__):
    """
    Call this into each file to setup a local logger for that file.\n
    This function will add the logs from its file to the global listener setup at the app initialization.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Send all logs from this logger to the global queue
    if not logger.handlers:
        logger.addHandler(QueueHandler(_log_queue))
        
    return logger

def space_decorator(file:str="app", log_dir:str="logs"):
    from os import getcwd as g
    path = f'{g()}\\{log_dir}\\{file}.log'
    try:
        with open(path, 'a') as f:
            f.write('\n')
    except Exception as e:
        print(f'space_operation failed\n{e}')