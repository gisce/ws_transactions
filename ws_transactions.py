# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011 Eduard Carreras i Nadal <ecarreras@gmail.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
"""This module adds transactions to XML-RPC level.
"""
import pooler
from service import security
from datetime import datetime, timedelta
import netsvc


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

    @property
    def psql_tid(self):
        """Get current PostgreSQL transaction ID
        """
        self._cursor.execute('''
            select txid_current()
        ''')
        return self._cursor.fetchone()[0]

    @property
    def psql_pid(self):
        """Get current PostgreSQL Process ID
        """
        self._cursor.execute('''
            select pg_backend_pid()
        ''')
        return self._cursor.fetchone()[0]
    
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
    """Service to allow XML-RPC transactions.
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
        self.exportMethod(self.close_connection)
        self.exportMethod(self.list)
        self.exportMethod(self.kill)
        self.log(netsvc.LOG_INFO, 'Ready for webservices transactions...')
        
    def log(self, log_level, message):
        """Logs througth netsvc.Logger().
        """
        logger = netsvc.Logger()
        logger.notifyChannel('ws-transaction', log_level, message)

    def list(self):
        for user in self.cursors:
            for trans, cursor in self.cursors[user].items():
                self.log(
                    netsvc.LOG_INFO,
                    'WSCursor opened by uid: %s id: %s tid: %s pid: %s '
                    'last accessed at %s.'
                    % (user, trans, cursor.psql_tid, cursor.psql_pid,
                       cursor.last_access.strftime('%Y-%m-%d %H:%M:%S'))
                )

    def kill(self, dbname, uid, passwd, transaction_id):
        """Kill WSCursor by transaction_id.
        """
        security.check(dbname, uid, passwd)
        cursor = self.get_cursor(uid, transaction_id)
        self.log(netsvc.LOG_INFO, 'Killing WSCursor %s...' % transaction_id)
        cursor.rollback()
        cursor.close()

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
    
    def begin(self, dbname, uid, passwd):
        """Starts a transaction for XML-RPC.
        """
        security.check(dbname, uid, passwd)
        self.cursors.setdefault(uid, {})
        database = pooler.get_db_and_pool(dbname)[0]
        cursor = database.cursor()
        sync_cursor = WSCursor(cursor)
        self.log(
            netsvc.LOG_INFO,
            'Creating a new transaction ID: %s TID: %s PID: %s' % (
                sync_cursor.psql_tid, sync_cursor.psql_tid,
                sync_cursor.psql_pid
            )
        )
        self.cursors[uid].update({sync_cursor.psql_tid: sync_cursor})
        return sync_cursor.psql_tid

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
            self.log(netsvc.LOG_DEBUG,
                'Executing from transaction ID: %s TID: %s PID: %s'
                % (transaction_id, sync_cursor.psql_tid, sync_cursor.psql_pid)
            )
            res = pool.execute_cr(cursor, uid, obj, method, *args, **kw)
        except Exception as exc:
            #self.rollback(dbname, uid, passwd, transaction_id)
            import traceback
            self.log(netsvc.LOG_ERROR,
                'Error within a transaction:\n'+
                traceback.format_exc())
            raise
        return res

    def rollback(self, dbname, uid, passwd, transaction_id):
        """Rollbacks XML-RPC transaction.
        """
        security.check(dbname, uid, passwd)
        sync_cursor = self.get_cursor(uid, transaction_id)
        self.log(netsvc.LOG_INFO,
            'Rolling back transaction ID: %s TID: %s PID: %s'
            % (transaction_id, sync_cursor.psql_tid, sync_cursor.psql_pid)
        )
        return sync_cursor.rollback()

    def commit(self, dbname, uid, passwd, transaction_id):
        """Commit XML-RPC transaction.
        """
        security.check(dbname, uid, passwd)
        sync_cursor = self.get_cursor(uid, transaction_id)
        self.log(netsvc.LOG_INFO,
            'Commiting transaction ID: %s TID: %s PID: %s'
            % (transaction_id, sync_cursor.psql_tid, sync_cursor.psql_pid)
        )
        return sync_cursor.commit()

    def close(self, dbname, uid, passwd, transaction_id):
        """Closes XML-RPC transaction.
        """
        security.check(dbname, uid, passwd)
        sync_cursor = self.get_cursor(uid, transaction_id)
        self.log(netsvc.LOG_INFO,
            'Closing transaction ID: %s TID: %s PID: %s'
            % (transaction_id, sync_cursor.psql_tid, sync_cursor.psql_pid)
        )
        res = sync_cursor.close()
        del self.cursors[uid][transaction_id]
        return res

    def close_connection(self, dbname, uid, passwd, transaction_id):
        """Alias for close"""
        self.close(dbname, uid, passwd, transaction_id)


WSTransactionService()
