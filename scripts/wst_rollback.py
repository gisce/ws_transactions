#!/usr/bin/env python

import xmlrpclib
import sys

def run_test(host, port, dbname, uid, pwd, tid):
    sock = xmlrpclib.ServerProxy('https://%s:%d/xmlrpc/ws_transaction'
                                 % (host, port))
    sock.rollback(dbname, uid, pwd, tid)
    sock.close(dbname, uid, pwd, tid)

if __name__ == "__main__":
    host, port, dbname, uid, pwd, tid = sys.argv[1:]
    port = int(port)
    uid = int(uid)
    tid = int(tid)
    run_test(host, port, dbname, uid, pwd, tid)
