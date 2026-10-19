"""Local SQLite snapshot creation/verification. Never overwrites a source or backup."""
import argparse
import os
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
import secrets

class BackupError(ValueError):pass

def readonly(path):
    path=Path(path).resolve()
    if not path.is_file():raise BackupError('Database file not found.')
    return sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=10)

def verify(path):
    try:
        db=readonly(path)
        try:
            version=db.execute('PRAGMA user_version').fetchone()[0]
            if not 1 <= version <= 7:raise BackupError('Unsupported MachineCare schema version; use matching application tooling.')
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            required={'users','sessions','parts','requests','maintenance','ledger','audit','buildings','lines','machines','types','compatibility','access','notifications'}
            if version>=2:required.add('line_access')
            if version>=4:required.update(('reorders','reorder_deliveries'))
            if version>=5:required.update(('alerts','alert_acknowledgements'))
            if version>=6:required.update(('job_state','email_outbox'))
            if version>=7:required.add('part_provenance')
            if not required.issubset(tables):raise BackupError('Required MachineCare tables are missing.')
            if db.execute('PRAGMA integrity_check').fetchall()!=[('ok',)]:raise BackupError('SQLite integrity check failed.')
            if db.execute('PRAGMA foreign_key_check').fetchone():raise BackupError('Foreign-key check failed.')
            return {'schema_version':version,'users':db.execute('SELECT COUNT(*) FROM users').fetchone()[0],'parts':db.execute('SELECT COUNT(*) FROM parts').fetchone()[0],'maintenance':db.execute('SELECT COUNT(*) FROM maintenance').fetchone()[0],'reorders':db.execute('SELECT COUNT(*) FROM reorders').fetchone()[0] if version>=4 else 0}
        finally:db.close()
    except sqlite3.Error as e:raise BackupError('Cannot verify this database: invalid, damaged or inaccessible SQLite file.') from e

def create(source,directory):
    source=Path(source).resolve();directory=Path(directory).resolve()
    if not source.is_file():raise BackupError('Source database not found. No database was created.')
    directory.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix='.machinecare-backup-',suffix='.db',dir=directory);os.close(fd)
    temp=Path(temp);final=None;owned_final=False
    try:
        src=readonly(source);dest=None
        try:
            dest=sqlite3.connect(temp)
            # SQLite's backup API captures a consistent snapshot, including WAL data.
            deadline=time.monotonic()+30
            def progress(status,remaining,total):
                if time.monotonic()>deadline:raise BackupError('Backup timed out. Retry when database activity is lower.')
            src.backup(dest,pages=128,progress=progress,sleep=0.05)
            # Session tokens must not regain validity if a backup is later restored.
            dest.execute('DELETE FROM sessions');dest.commit()
        finally:
            src.close()
            if dest is not None:dest.close()
        summary=verify(temp)
        name='machinecare_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+secrets.token_hex(4)+'.db'
        final=directory/name
        # Exclusive creation protects an existing file even if a name collides.
        out_fd=os.open(final,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);owned_final=True
        with os.fdopen(out_fd,'wb') as output,temp.open('rb') as input_file:
            import shutil
            shutil.copyfileobj(input_file,output)
            output.flush();os.fsync(output.fileno())
        summary=verify(final)
        owned_final=False
        return final,summary
    except sqlite3.Error as e:raise BackupError('Backup failed: database is inaccessible or invalid.') from e
    finally:
        temp.unlink(missing_ok=True)
        if owned_final and final is not None:final.unlink(missing_ok=True)

def main():
    parser=argparse.ArgumentParser(description='Create or verify a local MachineCare backup; no restore/overwrite operation is provided.')
    commands=parser.add_subparsers(dest='command',required=True)
    make=commands.add_parser('create');make.add_argument('--db',default='machinecare.db');make.add_argument('--out',default='backups')
    check=commands.add_parser('verify');check.add_argument('file')
    args=parser.parse_args()
    try:
        if args.command=='create':
            path,summary=create(args.db,args.out);print('Verified backup created:',path);print(summary);print('Backup sessions cleared; source sessions unchanged.')
        else:print('Backup verified:',verify(args.file))
    except (BackupError,OSError) as e:parser.exit(1,str(e)+'\n')

if __name__=='__main__':main()
