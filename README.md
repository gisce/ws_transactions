# XML-RPC WebService Transactions for OpenERP

This allows us to add another service endpoint `ws_transaction` to work with Transactions at XML-RPC level


## Examples

**Comit**

```python

DBNAME = 'test_ws_transactions'

sock = xmlrpclib.ServerProxy('http://localhost:8069/xmlrpc/ws_transaction')
tid = sock.begin(DBNAME, uid, password)
print("Opening transaction %s..." % tid)
partner1 = sock.execute(DBNAME, uid, PASS, tid, 'res.partner', 'read', [1],
                        ['name'])
print("Print before write", partner1[0])
sock.execute(DBNAME, uid, PASS, tid, 'res.partner', 'write', [1],
             {'name': '%s mod' % partner1[0]['name']})
partner1 = sock.execute(DBNAME, uid, PASS, tid, 'res.partner', 'read', [1],
                        ['name'])
print("Print after write", partner1[0])
print("Commit!")
sock.commit(DBNAME, uid, PASS, tid)
partner1 = sock.execute(DBNAME, uid, PASS, tid, 'res.partner', 'read', [1],
                        ['name'])
print("Print after commit", partner1[0])
print("Clossing...")
sock.close(DBNAME, uid, PASS, tid)
```


**Rollback**

```python

DBNAME = 'test_ws_transactions'

sock = xmlrpclib.ServerProxy('http://localhost:8069/xmlrpc/ws_transaction')
tid = sock.begin(DBNAME, uid, password)
print("Opening transaction %s..." % tid)
partner1 = sock.execute(DBNAME, uid, PASS, tid, 'res.partner', 'read', [1],
                        ['name'])
print("Print before write", partner1[0])
sock.execute(DBNAME, uid, PASS, tid, 'res.partner', 'write', [1],
             {'name': '%s mod' % partner1[0]['name']})
partner1 = sock.execute(DBNAME, uid, PASS, tid, 'res.partner', 'read', [1],
                        ['name'])
print("Print after write", partner1[0])
print("Rollback!")
sock.rollback(DBNAME, uid, PASS, tid)
partner1 = sock.execute(DBNAME, uid, PASS, tid, 'res.partner', 'read', [1],
                        ['name'])
print("Print after rollback", partner1[0])
print("Clossing...")
sock.close(DBNAME, uid, PASS, tid)
```
