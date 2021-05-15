#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import sys

# Logger global config
LOG_DIR = os.path.join("./")
LOG_FILE = "daemonize.log"
LOG_FORMAT = "%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s"

# Daemon setup
PID_FILE = "/daemon.pid"
# Daemon process running periodically, time interval setup (seconds).
TIME_INTERVAL = 2


def show_progress(index, buff_size):
    """
    Print progress onto console

    :param index: the current index of whole steps, type: integer
    :param buff_size: the whole length of steps, type: integer
    :return: None
    """
    sys.stdout.write("Collecting progress: "
                     "{0}/{1}\r".format((index + 1), buff_size))
    sys.stdout.flush()
