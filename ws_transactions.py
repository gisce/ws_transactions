# -*- encoding: utf-8 -*-
"""This module adds transactions to XML-RPC level.
"""
import pooler
from service import security
from datetime import datetime, timedelta
import netsvc
import threading

class WSCursor(object):
    """WebService Cursor.
    """
    def __init__(self, cursor, ttl=3600):
        self._cursor = cursor
        self.create_date = datetime.now()
        self.last_access = datetime.now()
        self.ttl = ttl
        
    @property
    def cursor(self):
        """Gets the cursor and updates last_accessed.
        """
        self.last_access = datetime.now()
        return self._cursor
    
    def close(self):
        """Closes the cursor.
        """
        self.cursor.close()
        
    def rollback(self):
        """Rollbacks the cursor.
        """
        return self.cursor.rollback()
        
    def commit(self):
        """Commit the cursor.
        """
        return self.cursor.commit()
        
    def is_abandoned(self):
        """Checks if the cursor is long away from ttl.
        """
        return datetime.now() > self.last_access + timedelta(seconds=self.ttl)

class WSTransactionService(netsvc.Service):
    """Sync service to allow XML-RPC transactions.
    """
    def __init__(self, name='ws_transaction'):
        """Init method.
        """
        netsvc.Service.__init__(self, name)
        self.joinGroup('web-services')
        self.cursors = {}
        self.exportMethod(self.begin)
        self.exportMethod(self.execute)
        self.exportMethod(self.rollback)
        self.exportMethod(self.commit)
        self.exportMethod(self.close)
        self.log(netsvc.LOG_INFO, 'Ready for webservices transactions...')
        self.tid = 0
        self.tid_protect = threading.Semaphore()
        
    def log(self, log_level, message):
        """Logs througth netsvc.Logger().
        """
        logger = netsvc.Logger()
        logger.notifyChannel('ws-transaction', log_level, message)
        
    def clean(self):
        """Clean abandoned cursors.
        """
        self.log(netsvc.LOG_INFO, 'Searching for abandoned transactions...')
        for user in self.cursors:
            for trans, cursor in self.cursors[user].items():
                if cursor.is_abandoned():
                    l_acc = cursor.last_accessed.strftime('%Y-%m-%d %H:%M:%S')
                    self.log(netsvc.LOG_INFO, 'Deleting transaction ID: %i. '
                                              'Last accessed on %s'
                                              % (trans, l_acc))
                    cursor.rollback()
                    cursor.close()
                    del self.cursors[trans]
    
    def get_transaction(self, dbname, uid, transaction_id):
        """Get transaction for all XML-RPC.
        """
        database = pooler.get_db_and_pool(dbname)[0]
        cursor = database.cursor()
        sync_cursor = WSCursor(cursor)
        self.log(netsvc.LOG_INFO, 'Creating a new transaction ID: %s'
                 % transaction_id)
        return {transaction_id: sync_cursor}
    
    def begin(self, dbname, uid, passwd, transaction_id=None):
        """Starts a transaction for XML-RPC.
        """
        security.check(dbname, uid, passwd)
        self.cursors.setdefault(uid, {})
        user_cursors = self.cursors[uid]
        if not transaction_id:
            self.tid_protect.acquire()
            self.tid += 1
            transaction_id = self.tid
            self.tid_protect.release()
        if transaction_id not in user_cursors:
            transaction = self.get_transaction(dbname, uid, transaction_id)
            self.cursors[uid].update(transaction)
        return transaction_id

    def get_cursor(self, uid, transaction_id):
        """Gets cursor and pool.
        """
        if transaction_id not in self.cursors.get(uid, {}):
            raise Exception("There are no Cursor for this transacion %s"
                            % transaction_id) 
        cursor = self.cursors[uid][transaction_id]
        return cursor

    def execute(self, dbname, uid, passwd, transaction_id, obj, method, *args,
                **kw):
        """Executes code with transaction_id.
        """
        security.check(dbname, uid, passwd)
        sync_cursor = self.get_cursor(uid, transaction_id)
        cursor = sync_cursor.cursor
        pool = pooler.get_db_and_pool(dbname)[1]
        try:
            self.log(netsvc.LOG_DEBUG, 'Executing from transaction ID: %s'
                     % transaction_id)
            res = pool.execute_cr(cursor, uid, obj, method, *args, **kw)
        except Exception, exc:
            self.rollback(dbname, transaction_id, uid, passwd)
            raise exc
        return res

    def rollback(self, dbname, uid, passwd, transaction_id):
        """Rollbacks XML-RPC transaction.
        """
        security.check(dbname, uid, passwd)
        sync_cursor = self.get_cursor(uid, transaction_id)
        self.log(netsvc.LOG_INFO, 'Rolling back transaction ID: %s'
                 % transaction_id)
        return sync_cursor.rollback()

    def commit(self, dbname, uid, passwd, transaction_id):
        """Commit XML-RPC transaction.
        """
        security.check(dbname, uid, passwd)
        sync_cursor = self.get_cursor(uid, transaction_id)
        self.log(netsvc.LOG_INFO, 'Commiting transaction ID: %s'
                 % transaction_id)
        return sync_cursor.commit()

    def close(self, dbname, uid, passwd, transaction_id):
        """Closes XML-RPC transaction.
        """
        security.check(dbname, uid, passwd)
        sync_cursor = self.get_cursor(uid, transaction_id)
        self.log(netsvc.LOG_INFO, 'Closing transaction ID: %s' % transaction_id)
        res = sync_cursor.close()
        del self.cursors[transaction_id]
        return res

WSTransactionService()
