#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
This file used for mech_engine log, it is based on logging module, we provides
3 types for split log:
1. Split by file size: default is 10M and the max backup count default is 100
2. Split by date: choices are: ['S', 'M', 'H', 'D', 'W0', 'W1', 'W2', 'W3',
'W4', 'W5', 'W6', 'midnight'] and the max backup count default is 100
3. Split by default: Wrong init type will trigger default split by 'D' with max
backup count is 3
If no input provides when init logger handler will apply type "1"
"""
import os
import logging

from logging import handlers
from daemon.comm.global_setup import (LOG_FILE, LOG_FORMAT, LOG_DIR)


class Logger(object):
    """ Class logger, based on logging module """

    log_level = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }

    def __init__(self, level='info', split=10485760, max_count=100):
        """
        Init function with default values

        :param level: default log level, type: str
        :param split: split type, default is 10M, type: int/str
        :param max_count: log max backup count, default is 100, type: int
        """
        file_name = LOG_FILE
        file_path = os.path.join(LOG_DIR, file_name)
        self.create_log_file(file_path)
        self.logger = logging.getLogger(file_path)
        # Set logging format
        format_str = logging.Formatter(LOG_FORMAT)
        # Set logging level
        self.logger.setLevel(self.log_level.get(level))
        # Print on screen
        screen = logging.StreamHandler()
        # Set screen display format
        screen.setFormatter(format_str)
        # Write to logging file
        if isinstance(split, str) and split in ['S', 'M', 'H', 'D', 'W0', 'W1', 'W2', 'W3', 'W4', 'W5', 'W6',
                                                'midnight']:
            # 1. Split log by time
            log = handlers.TimedRotatingFileHandler(filename=file_path, when=split, backupCount=max_count,
                                                    encoding='utf-8')
        elif isinstance(split, int):
            # 2. Split log by size, default is 10M
            log = handlers.RotatingFileHandler(filename=file_path, maxBytes=split, backupCount=max_count,
                                               encoding='utf-8')
        else:
            # 3. Giving run type split, will split by default
            print("ERROR: Wrong split type for log, choices are: ['S', 'M', "
                  "'H', 'D', 'W0', 'W1', 'W2', 'W3', 'W4', 'W5', 'W6', "
                  "'midnight'] or int, will apply default split by 'D' and the "
                  "max backup count for 3")
            log = handlers.TimedRotatingFileHandler(filename=file_path, when='D', backupCount=3, encoding='utf-8')
        # Set logging file format
        log.setFormatter(format_str)
        # Add logging object into logger
        self.logger.addHandler(screen)
        self.logger.addHandler(log)

    @property
    def level(self):
        """
        Get current logger level

        :return: current log level
        """
        return self.logger.level

    @level.setter
    def level(self, level):
        """
        Set logger level

        :param level: log level you want to set, type: str
        :return: None
        """
        self.logger.setLevel(self.log_level.get(level))
        for handler in self.logger.handlers:
            handler.setLevel(self.log_level.get(level))

    @classmethod
    def create_log_file(cls, file_path):
        """
        Create log file under giving filepath

        :param file_path: filepath for log file, type: str
        :return: None
        """
        try:
            if not os.path.exists(LOG_DIR):
                os.makedirs(LOG_DIR)
        except Exception as err:
            raise RuntimeError("Not able to create log directory with error: %s"
                               ", please check your cluster!" % err)
        with open(file_path, 'a') as fw:
            fw.close()


# Define default logger handler, split by file size of 10M
logHandler = Logger()
logger = logHandler.logger
