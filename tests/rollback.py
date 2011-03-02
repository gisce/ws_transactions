#!/usr/bin/env python
# -*- coding: utf-8 -*-
import xmlrpclib

HOST = 'localhost'
PORT = 8069
USER = 'admin'
PASS = 'admin'
DBNAME = 'openerp'

def run_test():
    sock = xmlrpclib.ServerProxy('http://%s:%d/xmlrpc/common' % (HOST, PORT))
    uid = sock.login(DBNAME, USER, PASS)
    sock = xmlrpclib.ServerProxy('http://%s:%d/xmlrpc/ws_transaction'
                                 % (HOST, PORT))
    print "UID: %s PASS: %s" % (uid, PASS)
    tid = sock.begin(DBNAME, uid, PASS)
    print "Opening transaction %s..." % tid
    partner1 = sock.execute(DBNAME, uid, PASS, tid, 'res.partner', 'read', [1],
                            ['name'])
    print "Print before write", partner1[0]
    sock.execute(DBNAME, uid, PASS, tid, 'res.partner', 'write', [1],
                 {'name': '%s mod' % partner1[0]['name']})
    partner1 = sock.execute(DBNAME, uid, PASS, tid, 'res.partner', 'read', [1],
                            ['name'])
    print "Print after write", partner1[0]
    print "Rollback!"
    sock.rollback(DBNAME, uid, PASS, tid)
    partner1 = sock.execute(DBNAME, uid, PASS, tid, 'res.partner', 'read', [1],
                            ['name'])
    print "Print after rollback", partner1[0]
    print "Clossing..."
    sock.close(DBNAME, uid, PASS, tid)

if __name__ == "__main__":
    run_test()
