import sqlite3
from config import DATABASE_PATH
class DB:
 def __init__(self): self.init()
 def conn(self): c=sqlite3.connect(DATABASE_PATH); c.row_factory=sqlite3.Row; return c
 def init(self):
  with self.conn() as c:
   c.executescript("""
   CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY,username TEXT,name TEXT,balance REAL NOT NULL DEFAULT 0,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
   CREATE TABLE IF NOT EXISTS deposits(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,username TEXT,amount REAL,trxid TEXT UNIQUE,status TEXT DEFAULT 'PENDING',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
   CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,ff_uid TEXT,server TEXT,likes INTEGER,price REAL,status TEXT,provider_order TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
   CREATE TABLE IF NOT EXISTS ledger(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,amount REAL,kind TEXT,reference TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
   """)
 def ensure_user(self,uid,username,name):
  with self.conn() as c: c.execute("INSERT INTO users(user_id,username,name) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,name=excluded.name",(uid,username,name))
 def balance(self,uid):
  with self.conn() as c:
   r=c.execute("SELECT balance FROM users WHERE user_id=?",(uid,)).fetchone(); return float(r["balance"]) if r else 0
 def create_deposit(self,uid,username,amount,trxid):
  with self.conn() as c: cur=c.execute("INSERT INTO deposits(user_id,username,amount,trxid) VALUES(?,?,?,?)",(uid,username,amount,trxid)); return cur.lastrowid
 def get_deposit(self,did):
  with self.conn() as c:
   r=c.execute("SELECT * FROM deposits WHERE id=?",(did,)).fetchone(); return dict(r) if r else None
 def approve_deposit(self,did):
  with self.conn() as c:
   r=c.execute("SELECT * FROM deposits WHERE id=? AND status='PENDING'",(did,)).fetchone()
   if not r: return
   c.execute("UPDATE deposits SET status='APPROVED' WHERE id=?",(did,))
   c.execute("UPDATE users SET balance=balance+? WHERE user_id=?",(r["amount"],r["user_id"]))
   c.execute("INSERT INTO ledger(user_id,amount,kind,reference) VALUES(?,?,?,?)",(r["user_id"],r["amount"],"DEPOSIT",str(did)))
 def reject_deposit(self,did):
  with self.conn() as c: c.execute("UPDATE deposits SET status='REJECTED' WHERE id=? AND status='PENDING'",(did,))
 def create_order(self,uid,ffuid,server,likes,price):
  with self.conn() as c:
   r=c.execute("SELECT balance FROM users WHERE user_id=?",(uid,)).fetchone()
   if not r or r["balance"]<price: return None
   c.execute("UPDATE users SET balance=balance-? WHERE user_id=?",(price,uid))
   cur=c.execute("INSERT INTO orders(user_id,ff_uid,server,likes,price,status) VALUES(?,?,?,?,?,'PROCESSING')",(uid,ffuid,server,likes,price))
   c.execute("INSERT INTO ledger(user_id,amount,kind,reference) VALUES(?,?,?,?)",(uid,-price,"ORDER",str(cur.lastrowid)))
   return cur.lastrowid
 def finish_order(self,oid,status,provider,likes):
  with self.conn() as c: c.execute("UPDATE orders SET status=?,provider_order=?,likes=? WHERE id=?",(status,str(provider),likes,oid))
 def refund_order(self,oid,status):
  with self.conn() as c:
   r=c.execute("SELECT * FROM orders WHERE id=? AND status='PROCESSING'",(oid,)).fetchone()
   if not r: return
   c.execute("UPDATE users SET balance=balance+? WHERE user_id=?",(r["price"],r["user_id"]))
   c.execute("UPDATE orders SET status=? WHERE id=?",(status,oid))
   c.execute("INSERT INTO ledger(user_id,amount,kind,reference) VALUES(?,?,?,?)",(r["user_id"],r["price"],"REFUND",str(oid)))
 def order_count(self,uid):
  with self.conn() as c: return c.execute("SELECT COUNT(*) n FROM orders WHERE user_id=?",(uid,)).fetchone()["n"]
 def likes_total(self,uid):
  with self.conn() as c: return c.execute("SELECT COALESCE(SUM(likes),0) n FROM orders WHERE user_id=? AND status='SUCCESS'",(uid,)).fetchone()["n"]
 def orders(self,uid):
  with self.conn() as c: return [dict(x) for x in c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 20",(uid,))]
 def deposit_history(self,uid):
  with self.conn() as c: return [dict(x) for x in c.execute("SELECT * FROM deposits WHERE user_id=? ORDER BY id DESC LIMIT 20",(uid,))]
 def all_users(self):
  with self.conn() as c: return [dict(x) for x in c.execute("SELECT user_id,username,name,balance FROM users ORDER BY created_at DESC LIMIT 100")]
 def pending_deposits(self):
  with self.conn() as c: return [dict(x) for x in c.execute("SELECT * FROM deposits WHERE status='PENDING' ORDER BY id")]
 def all_deposits(self):
  with self.conn() as c: return [dict(x) for x in c.execute("SELECT * FROM deposits ORDER BY id DESC LIMIT 100")]
 def all_orders(self):
  with self.conn() as c: return [dict(x) for x in c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 100")]
 def admin_balance(self,uid,action,amount):
  with self.conn() as c:
   r=c.execute("SELECT balance FROM users WHERE user_id=?",(uid,)).fetchone()
   if not r: return
   if action=="add": new=r["balance"]+amount
   elif action=="sub": new=max(0,r["balance"]-amount)
   else: new=max(0,amount)
   delta=new-r["balance"]
   c.execute("UPDATE users SET balance=? WHERE user_id=?",(new,uid))
   c.execute("INSERT INTO ledger(user_id,amount,kind,reference) VALUES(?,?,?,?)",(uid,delta,"ADMIN_ADJUST","admin"))
 def stats(self):
  with self.conn() as c:
   return {"users":c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"],
   "orders":c.execute("SELECT COUNT(*) n FROM orders").fetchone()["n"],
   "success":c.execute("SELECT COUNT(*) n FROM orders WHERE status='SUCCESS'").fetchone()["n"],
   "likes":c.execute("SELECT COALESCE(SUM(likes),0) n FROM orders WHERE status='SUCCESS'").fetchone()["n"],
   "deposits":c.execute("SELECT COALESCE(SUM(amount),0) n FROM deposits WHERE status='APPROVED'").fetchone()["n"]}
