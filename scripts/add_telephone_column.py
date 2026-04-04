"""Script one-shot : ajoute la colonne telephone a users si elle manque."""
import sqlite3
import os

basedir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(basedir, 'salon.db')

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("PRAGMA table_info(users)")
cols = [row[1] for row in cur.fetchall()]

if 'telephone' not in cols:
    cur.execute("ALTER TABLE users ADD COLUMN telephone VARCHAR(20)")
    conn.commit()
    print("Colonne telephone ajoutee avec succes.")
else:
    print("La colonne telephone existe deja.")

conn.close()
