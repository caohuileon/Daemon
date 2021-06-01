#!/usr/bin/env python
# encoding: utf-8

"""
Author: Leon
Date: 2021-05-15
Python Version: 3.8.x
Description: This module is used to daemonize a process. You can copy the whole directory to any of your code repo then
use it.

Usage:
python3 daemonize.py -h
usage: daemonize.py [-h] [--interval <Interval Time>] [--verbose <True|False>] [--path <Work path>]
[--umask <File umask>] <process file> <start|stop|restart|status>

positional arguments:
  <process file>        Which process you want to run as daemon.
  <start|stop|restart|status>
                        What action to perform.

optional arguments:
  -h, --help            show this help message and exit
  --interval <Interval Time>
                        Daemon process running interval. Default (seconds): [300].
  --verbose <True|False>
                        Debug mode switch. Default: [False]
  --path <Work path>    Default working path. Default: ["/"]
  --umask <File umask>  File umask. Default: [0]

Arguments:
:arg:process: Process file abs-path you want to run, type: str
:arg:action: What action you want to perform, type: str
:arg:interval: Daemonize process running interval time (seconds), default: [300], type: int
:arg:verbose: Debug mode to control whether print log on screen or just in log file, default: [False], type: bool
              Since we use logger module, so this parameter can be ignored.
:arg:patch: Default working path, beware the pid file path is locked in "/daemon.pid". default: ["/"], type: str
:arg:umask: File mask access privilege, recommend set to 0. default: [0], type: int
"""

import argparse
import atexit
import os
import signal
import sys
import time

from daemon.comm.logger import logger
from daemon.comm.global_setup import PID_FILE


class CDaemon(object):

    def __init__(self, pid_file=PID_FILE, stdin=os.devnull, stdout=os.devnull, stderr=os.devnull):
        """
        Init function

        :param pid_file: PID file path, type: str
        :param stdin: Standard STDIN, default: os.devnull, type: I/O object
        :param stdout: Standard STDOUT, default: os.devnull, type: I/O object
        :param stderr: Standard STDERR, default: os.devnull, type: I/O object
        """
        self.pid_file = pid_file
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.daemon_alive = True
        # Args setup
        args = self.get_args()
        self.process = args.process
        self.action = args.action
        # Process running interval time
        self.interval = args.interval
        self.path = args.path
        # Debug mode setup
        self.verbose = args.verbose
        # File mask, default 0
        self.umask = args.umask

    @staticmethod
    def get_args():
        """
        This function is parse user CLI input values, it supports components level

        :return: The args user input, type: object
        """
        parser = argparse.ArgumentParser()
        parser.add_argument('process', metavar='<process file>', help='Which process you want to run as daemon.')
        parser.add_argument('action', metavar='<start|stop|restart|status>', help='What action to perform.',
                            choices=['start', 'stop', 'restart', 'status'])
        parser.add_argument('--interval', type=int, metavar='<Interval Time>', help='Daemon process running interval. '
                            'Default (seconds): [300].',
                            default=300)
        parser.add_argument('--verbose', type=bool, metavar='<True|False>', help='Debug mode switch. Default: [False]',
                            default=False)
        parser.add_argument('--path', type=str, metavar='<Work path>', help='Default working path. Default: ["/"]',
                            default='/')
        parser.add_argument('--umask', type=int, metavar='<File umask>', help='File umask. Default: [0]', default=0)
        args = parser.parse_args()
        return args

    def switch_verbose(self):
        """
        Switch debug mode to control print log on screen or just in log file.

        :return: None
        """
        # Verbose mode ON is print log on screen, since we use logger so its ON/OFF is not useful
        if self.verbose:
            logger.info("Verbose switch ON")
            self.stdin = sys.stdin
            self.stdout = sys.stdout
            self.stderr = sys.stderr
        # Verbose mode OFF
        else:
            logger.info("Verbose switch OFF")
            self.stdin = os.devnull
            self.stdout = os.devnull
            self.stderr = os.devnull

    @classmethod
    def fork_sub_process(cls):
        """
        Fork process and make sure father process will exit.

        :return: None
        """
        try:
            pid = os.fork()
            # If current running on main process (pid > 0) then exit main process, handler over to sub-process
            if pid > 0:
                # sys.exit() will call register callback function del_pid
                sys.exit(0)
        except OSError as err:
            logger.error("ERROR: Fork sub process failed: %d, %s" % (err.errno, err.strerror))
            sys.stderr.write("ERROR: Fork sub process failed: %d, %s" % (err.errno, err.strerror))
            sys.exit(1)

    def redirect_std_info(self):
        """
        Redirect STD I/O object

        :return: None
        """
        logger.info("Redirecting std info and file description objects...")
        logger.warning("After redirect all log will not show in console, you may need check daemon status by command "
                       "or in log file!")
        sys.stdout.flush()
        sys.stderr.flush()

        with open(self.stdin, 'r') as s_in:
            os.dup2(s_in.fileno(), sys.stdin.fileno())
        with open(self.stdout, 'a+') as s_out:
            os.dup2(s_out.fileno(), sys.stdout.fileno())
        if self.stderr:
            with open(self.stderr, 'a+') as s_err:
                os.dup2(s_err.fileno(), sys.stderr.fileno())

    # This is main function to daemonize a process
    def daemonize(self):
        """
        The main function to prepare a daemon environment.
        It has 6 steps:
        1. Fork main process and make sure sub process running as PGID leader
        2. Create new session SID in sub progress
        3. Switch working directory to new default and reset file access umask privilege
        4. Second fork sub process to a new grand sub progress and handover it to system init progress pid(1)
        5. Close all not used file description objects which in sub progress and redirect them
        6. Register exit call back function to process tasks after receiving exit signal.

        :return: None
        """
        # Step 1: Create sub process by using fork
        logger.info("Step 1: Create sub process...")
        self.fork_sub_process()

        # Step 2: Create new session in sub process by using setsid
        logger.info("Step 2: Create new session id...")
        os.setsid()    # After setsid, sub-process pid will > 0 and will be host of pgid

        # Step 3: Switch current working directory and reset file umask privilege
        logger.info("Step 3: Switch current working directory and reset file umask privilege...")
        os.chdir(self.path)
        os.umask(self.umask)

        # Step 4: Second fork grand sub-process
        logger.info("Step 4: Second forking sub-process...")
        self.fork_sub_process()

        # Step 5: Close not used file description objects
        logger.info("Step 5: Closing not used file description objects...")
        self.redirect_std_info()

        # Step 6: Register exit callback and listening signal interruption
        logger.info("Step 6: Registering exit callback and listening signal interruption...")
        # Register exit callback function
        atexit.register(self.del_pid)
        pid = str(os.getpid())
        with open(self.pid_file, 'w+') as fw:
            fw.write('%s\n' % pid)

        # Watching signal interrupt. Add signal callback here to better process system exit behavior.
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGHUP, self.signal_handler)

    def signal_handler(self):
        """
        Register callback function on receiving interrupt signal during prepare daemon environment.
        Note: it will only take effects in this function.

        :return: None
        """
        logger.info("Received interrupt signal, processing exit callback...")
        self.daemon_alive = False
        sys.exit(0)

    def get_pid(self):
        """
        Get current progress PID

        :return: None
        """
        try:
            with open(self.pid_file, 'r') as fr:
                pid = int(fr.read().strip())
                fr.close()
        except IOError:
            pid = None
        except SystemExit:
            pid = None
        return pid

    def del_pid(self):
        """
        Delete PID callback function. This function will be called on sys.exit to delete pid file.

        :return: None
        """
        logger.info("Deleting pid file...")
        if os.path.exists(self.pid_file):
            os.remove(self.pid_file)
        self.daemon_alive = False

    def start(self, *args, **kwargs):
        """
        Start a daemon progress

        :param args: Tuple args input, type: tuple
        :param kwargs: Dict args input, type: dict
        :return: None
        """
        logger.info("Starting daemon process...")
        # checking pid file to see if the daemon already running
        pid = self.get_pid()
        if pid:
            msg = 'pid file %s already exists, is daemon process already running?\n'
            logger.info(msg % self.pid_file)
            sys.stderr.write(msg % self.pid_file)
            sys.exit(1)
        # Prepare daemon context
        self.daemonize()
        # Start daemon process
        self.run(*args, **kwargs)

    def stop(self):
        """
        Terminate a daemon progress

        :return: None
        """
        logger.info("Stopping daemon process...")
        # Get pid
        try:
            pid = self.get_pid()
        except IOError:
            pid = None

        # If process not run return
        if not pid:
            msg = 'pid file [%s] not exists, daemon process NOT running!\n'
            logger.info(msg % self.pid_file)
            sys.stderr.write(msg % self.pid_file)
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
            return

        # Try to kill daemon process
        try:
            i = 0
            while True:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
                i = i + 1
                if i % 10 == 0:
                    os.kill(pid, signal.SIGHUP)
        except OSError as err:
            err = str(err)
            if err.find('No such process') > 0:
                if os.path.exists(self.pid_file):
                    os.remove(self.pid_file)
            else:
                logger.error("Catch error info: %s while stopping!" % str(err))
                sys.exit(1)
        logger.info("Daemon process stopped successfully!")

    def restart(self, *args, **kwargs):
        """
        Restart a daemon progress

        :param args: Tuple args input, type: tuple
        :param kwargs: Dict args input, type: dict
        :return: None
        """
        logger.info("Restarting daemon...")
        self.stop()
        self.start(*args, **kwargs)

    def status(self):
        """
        Check current daemon service status

        :return: None
        """
        logger.info("Checking daemon status...")
        try:
            pid = self.get_pid()
        except IOError:
            pid = None

        if not pid:
            message = "No such process running.\n"
            logger.info(message)
            sys.stderr.write(message)
        else:
            message = "The process is running, PID is %s .\n"
            logger.info(message % str(pid))
            sys.stderr.write(message % str(pid))

    def run(self, *args, **kwargs):
        """
        Run exact process you want as daemon service. You should put your process in this function.
        Usage: You can use this by bellow suggestions:
        1. Your process should running independently, then put your running command here to call it.
        2. Your can copy the whole daemon code into your project then integrate with your project.
        3. Suggest call your process with sync/block ways, it will make sure your process will not running concurrently
           only except the situation you want it to. You can use: os.system(command), subprocess.call(command).etc.

        :param args: Tuple args input, type: tuple
        :param kwargs: Dict args input, type: dict
        :return: None
        """
        logger.info("Daemon process start running...")
        while True:
            logger.info(self.process)
            logger.warning("Process will rerun after %s seconds." % self.interval)
            time.sleep(self.interval)


def show_title_info(action, process, interval):
    """
    Show title brief info

    :param action: User actions, type: str
    :param process: User process, type: str
    :param interval: User interval time, type: int
    :return: None
    """
    logger.info("=========================================== Daemon Begin ============================================")
    logger.info("Daemon Action: %s, Process: '%s', Interval: %ss" % (action, process, interval))
    logger.info("=====================================================================================================")


def show_end_info():
    """ Show end info """
    logger.info("============================================= Daemon End ============================================")


def main():
    """ Main Function """
    daemon = CDaemon()
    show_title_info(daemon.action, daemon.process, daemon.interval)
    # Watching verbose change
    daemon.switch_verbose()
    if daemon.action == "start":
        daemon.start()
    elif daemon.action == "stop":
        daemon.stop()
    elif daemon.action == "restart":
        daemon.restart()
    elif daemon.action == "status":
        daemon.status()
    show_end_info()


if __name__ == '__main__':
    main()
