# -*- coding: utf-8 -*-
import imp
import os
import sys
import unittest

import six


class FakeCommon(object):
    def login(self, database, user, password):
        return 7


class FakeTransaction(object):
    def __init__(self):
        self.actions = []
        self.name = 'Original'

    def begin(self, *args):
        return 11

    def execute(self, database, uid, password, transaction, model,
                method, ids, values):
        if method == 'write':
            self.name = values['name']
            return True
        return [{'name': self.name}]

    def commit(self, *args):
        self.actions.append('commit')

    def rollback(self, *args):
        self.actions.append('rollback')

    def close(self, *args):
        self.actions.append('close')


class FakeXmlRpc(object):
    def __init__(self):
        self.transaction = FakeTransaction()

    def ServerProxy(self, url):
        if url.endswith('/common'):
            return FakeCommon()
        return self.transaction


class ManualTransactionScriptsTest(unittest.TestCase):
    def run_script(self, name):
        fake_xmlrpc = FakeXmlRpc()
        old_module = sys.modules.get('xmlrpclib')
        old_stdout = sys.stdout
        sys.modules['xmlrpclib'] = fake_xmlrpc
        sys.stdout = six.StringIO()
        try:
            path = os.path.join(os.path.dirname(__file__), name + '.py')
            module = imp.load_source('ws_transactions_' + name, path)
            module.run_test()
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
            if old_module is None:
                del sys.modules['xmlrpclib']
            else:
                sys.modules['xmlrpclib'] = old_module
        self.assertIn(name.title() + '!', output)
        self.assertEqual([name, 'close'], fake_xmlrpc.transaction.actions)

    def test_commit_script_executes_transaction(self):
        self.run_script('commit')

    def test_rollback_script_executes_transaction(self):
        self.run_script('rollback')


if __name__ == '__main__':
    unittest.main()
