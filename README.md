# Description
This repo used for Daemon module and this module can be easily copy to your code to daemonize your project.\
Python Version: 3.8.x

## Daemonize Steps
* Fork main process and make sure sub process running as PGID leader
* Create new session SID in sub progress
* Switch working directory to new default and reset file access umask privilege
* Second fork sub process to a new grand sub progress and handover it to system init progress pid(1)
* Close all not used file description objects which in sub progress and redirect them
* Register exit call back function to process tasks after receiving exit signal.

# Usage
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

# Arguments
    :arg:process: Process file abs-path you want to run, type: str
    :arg:action: What action you want to perform, type: str
    :arg:interval: Daemonize process running interval time (seconds), default: [300], type: int
    :arg:verbose: Debug mode to control whether print log on screen or just in log file, default: [False], type: bool
                  Since we use logger module, so this parameter can be ignored.
    :arg:patch: Default working path, beware the pid file path is locked in "/daemon.pid". default: ["/"], type: str
    :arg:umask: File mask access privilege, recommend set to 0. default: [0], type: int
