import json
import sqlite3
from pathlib import Path
from platformdirs import user_data_dir

class Storage:
    def __init__(self):
        self.root = Path(user_data_dir('FGTSGuias', 'FGTSGuias'))
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / 'local.sqlite3')
        self.db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS jobs (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS decisions (id TEXT PRIMARY KEY, value TEXT NOT NULL)')
        self.db.commit()

    def get(self, key, default=None):
        row = self.db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self, key, value):
        self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, json.dumps(value)))
        self.db.commit()

    def job_key(self, company, initial, final):
        return ':'.join([company['cnpj'], initial, final])

    def job(self, key):
        row = self.db.execute('SELECT value FROM jobs WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def save_job(self, key, value):
        self.db.execute('INSERT OR REPLACE INTO jobs VALUES (?,?)', (key, json.dumps(value)))
        self.db.commit()

    def record_decision(self, value):
        self.db.execute('INSERT INTO decisions VALUES (?,?)', (value['id'], json.dumps(value)))
        self.db.commit()
