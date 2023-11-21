#! /usr/bin/env python
import time
import daemon
import os
import db_replicator

class App():
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/tty'
        self.stderr_path = '/dev/tty'
        self.pidfile_path =  '/tmp/foo.pid'
        self.pidfile_timeout = 5
    def run(self):
        while True:
            db_replicator.run()
            time.sleep(100)

app = App()
with daemon.DaemonContext():
    app.run()
