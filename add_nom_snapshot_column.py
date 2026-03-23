"""Script one-shot : ajoute la colonne nom_snapshot a rdv_supplements si elle manque."""
import sqlite3
import os

basedir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(basedir, 'salon.db')

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("PRAGMA table_info(rdv_supplements)")
cols = [row[1] for row in cur.fetchall()]

if 'nom_snapshot' not in cols:
    cur.execute("ALTER TABLE rdv_supplements ADD COLUMN nom_snapshot VARCHAR(100) DEFAULT ''")
    conn.commit()
    print("Colonne nom_snapshot ajoutee avec succes.")
else:
    print("La colonne nom_snapshot existe deja.")

conn.close()
