#!/usr/bin/env python
# encoding: utf-8

import argparse
import atexit
import os
import signal
import sys
import time
import traceback

from daemon.comm.logger import logger
from daemon.comm.global_setup import PID_FILE


class CDaemon(object):

    def __init__(self, pid_file=PID_FILE, stdin=os.devnull, stdout=os.devnull, stderr=os.devnull):
        self.pid_file = pid_file
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.daemon_alive = True
        # Args setup
        args = self.get_args()
        self.process = args.process
        self.action = args.action
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
        parser.add_argument('--verbose', type=bool, metavar='<True|False>', help='Debug mode switch. Default: [False]',
                            default=False)
        parser.add_argument('--path', type=str, metavar='<Work path>', help='Default working path. Default: ["/"]',
                            default='/')
        parser.add_argument('--umask', type=int, metavar='<File umask>', help='File umask. Default: [0]', default=0)
        args = parser.parse_args()
        return args

    def switch_verbose(self):
        if self.verbose:
            logger.info("Verbose switch ON")
            self.stdin = sys.stdin
            self.stdout = sys.stdout
            self.stderr = sys.stderr
        else:
            logger.info("Verbose switch OFF")
            self.stdin = os.devnull
            self.stdout = os.devnull
            self.stderr = os.devnull

    @classmethod
    def fork_sub_process(cls):
        try:
            pid = os.fork()
            # If current running on main process (pid > 0) then exit main process, handler over to sub-process
            if pid > 0:
                sys.exit(0)
        except OSError as err:
            logger.error("ERROR: Fork sub process failed: %d, %s" % (err.errno, err.strerror))
            sys.stderr.write("ERROR: Fork sub process failed: %d, %s" % (err.errno, err.strerror))
            sys.exit(1)

    def redirect_std_info(self):
        logger.info("Redirecting std info and file description objects...")
        sys.stdout.flush()
        sys.stderr.flush()

        with open(self.stdin, 'r') as s_in:
            os.dup2(s_in.fileno(), sys.stdin.fileno())
        with open(self.stdout, 'a+') as s_out:
            os.dup2(s_out.fileno(), sys.stdout.fileno())
        # if self.stderr:
        #     with open(self.stderr, 'a+') as s_err:
        #         os.dup2(s_err.fileno(), sys.stderr.fileno())

    # This is main function to daemonize a process
    def daemonize(self):
        # Step 1: Create sub process by using fork
        logger.info("Step 1: Create sub process...")
        self.fork_sub_process()

        # Step 2: Create new session in sub process by using setsid
        logger.info("Step 2: Create new session id...")
        os.setsid()    # After setsid, sub-process pid will > 0 and will be host of pgid

        # Step 3: Switch current working directory and reset file umask privilege
        logger.info("Step3: Switch current working directory and reset file umask privilege...")
        os.chdir(self.path)
        os.umask(self.umask)

        # Step 4: Second fork grand sub-process
        logger.info("Step 4: Second forking sub-process...")
        self.fork_sub_process()

        # Step 5: Close not used file description objects
        logger.info("Step 5: Closing not used file description objects...")
        self.redirect_std_info()

        # Step 6: Monitoring exit behavior
        logger.info("Step 6: Monitoring exit behavior...")
        # Register exit callback function
        atexit.register(self.del_pid)
        pid = str(os.getpid())
        with open(self.pid_file, 'w+') as fw:
            fw.write('%s\n' % pid)

        # Watching signal interrupt
        def signal_handler():
            self.daemon_alive = False
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def get_pid(self):
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
        logger.info("Deleting pid file...")
        if os.path.exists(self.pid_file):
            os.remove(self.pid_file)

    def start(self, *args, **kwargs):
        logger.info("Starting daemon process...")
        # checking pid file to see if the daemon already running
        pid = self.get_pid()
        if pid:
            msg = 'pid file %s already exists, is daemon process already running?\n'
            sys.stderr.write(msg % self.pid_file)
            sys.exit(1)
        # Prepare daemon context
        self.daemonize()
        # Start daemon process
        self.run(*args, **kwargs)

    def stop(self):
        logger.info("Stopping daemon process...")
        pid = self.get_pid()
        if not pid:
            msg = 'pid file [%s] does not exist. is daemon process NOT running?\n' % self.pid_file
            sys.stderr.write(msg)
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
            return
        # try to kill the daemon process
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
            if self.verbose >= 1:
                logger.info("Daemon stopped successfully!")

    def restart(self, *args, **kwargs):
        logger.info("Restarting daemon...")
        self.stop()
        self.start(*args, **kwargs)

    def status(self):
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
        logger.info("Daemon process start running...")
        while True:
            sys.stdout.write('%s: hello world\n' % (time.ctime(),))
            sys.stdout.flush()
            time.sleep(2)


def show_title_info(action, process):
    logger.info("=========================================== Daemon Begin ============================================")
    logger.info("Daemon Action: %s, Process: %s" % (action, process))
    logger.info("=====================================================================================================")


def show_end_info():
    logger.info("============================================= Daemon End ============================================")


def main():
    daemon = CDaemon()
    show_title_info(daemon.action, daemon.process)
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
