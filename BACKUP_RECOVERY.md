# Recovery drill using a separate database

Current backup tooling validates supported schemas 1–6, so older databases can be backed up before upgrading. Code now migrates to schema 7; part_provenance preserves supplied identifiers and marks demo inventory assumptions. Job/outbox state is included in v6 backups; keep email delivery disabled after recovery until sent/uncertain events are reconciled with the SMTP provider to avoid replaying post-snapshot deliveries. A v4 -> v6 separate-copy recovery drill passed on 2026-10-12; see PROJECT_STATUS.md. Windows ACLs and encrypted/off-host retention still require an approved deployment policy.

Test on a disposable project copy first. A backup is a point-in-time snapshot; work recorded after it was created is absent from that snapshot. The backup tool does not automatically replace your live database or offer a destructive restore command.

1. Create a backup and verify the printed path:

```powershell
cd F:\work\machinecare_flutter\backend
python backup.py create --db .\machinecare.db --out F:\MachineCareBackups
python backup.py verify "F:\MachineCareBackups\YOUR_BACKUP_FILENAME.db"
```

2. Stop Flutter with `q` and the backend with Ctrl+C.

3. Set the actual backup path, then copy it to a new recovery filename. This command checks for an existing destination and does not overwrite it:

```powershell
$savedBackup = 'F:\MachineCareBackups\YOUR_BACKUP_FILENAME.db'
$recoveryDb = 'F:\work\machinecare_flutter\backend\machinecare_recovery_test.db'
if (Test-Path $recoveryDb) {
    throw 'Recovery file already exists. Choose a different new filename.'
}
Copy-Item -LiteralPath $savedBackup -Destination $recoveryDb
python backup.py verify $recoveryDb
```

Keep the original `machinecare.db` in place. Do not reuse a filename with existing `-wal` or `-shm` sidecar files; choose a completely new filename for this drill.

4. Start the backend explicitly using the recovery copy:

```powershell
$env:MACHINECARE_ORIGIN = 'http://localhost:18080'
python server.py run --db $recoveryDb
```

5. Start Flutter in another terminal using your normal Chrome command. Sign in using an account/password valid when the backup was created. Verify machine counts, physical/reserved/available stock, history, partial deliveries, alerts and audit records against that snapshot. Old browser sessions are invalid because backup sessions were cleared. Do not enter live maintenance or real deliveries during a recovery drill.

6. After checking, stop both services. To return to the original current database, start the backend with:

```powershell
python server.py run --db .\machinecare.db
```

Restart Flutter and sign in. Keep recovery-test files separate from live backups.

For an actual recovery, use the verified recovered database with the matching/current supported app code and explicitly keep passing its path with `--db` in future launches and backup commands. Confirm which database is active before recording real work. Restored data has no changes after the backup time. No automatic data merge is provided.
