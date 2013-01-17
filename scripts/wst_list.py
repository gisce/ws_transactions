#!/usr/bin/env python

import xmlrpclib
import sys

def run_test(host, port):
    sock = xmlrpclib.ServerProxy('https://%s:%d/xmlrpc/ws_transaction'
                                 % (host, port))
    tid = sock.list()

if __name__ == "__main__":
    host = sys.argv[1]
    port = int(sys.argv[2])
    run_test(host, port)
