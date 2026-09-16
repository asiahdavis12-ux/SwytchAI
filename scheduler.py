# scheduler.py — SwytchAI Scheduled Config Backups (Configurable)
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

scheduler = BackgroundScheduler()

def run_backup(app, org_id=None):
    """Pull configs from all devices (or for a specific org)."""
    with app.app_context():
        import sqlite3
        from napalm_engine import create_device

        conn = sqlite3.connect("swytchai.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if org_id:
            cursor.execute("SELECT * FROM devices WHERE org_id = ?", (org_id,))
        else:
            cursor.execute("SELECT * FROM devices")
        devices = [dict(row) for row in cursor.fetchall()]

        results = {"success": 0, "failed": 0, "errors": []}

        for device in devices:
            try:
                dd = {
                    "host": device["host"],
                    "username": device["username"],
                    "password": device["password"],
                    "vendor": device["vendor"],
                }
                dev = create_device(dd)
                dev.connect()
                config = dev.get_config()
                dev.disconnect()

                running_config = config.get("running", "")

                cursor.execute("""
                    INSERT INTO config_backups (device_id, org_id, hostname, config_text, backup_type, status, created_at)
                    VALUES (?, ?, ?, ?, 'scheduled', 'success', ?)
                """, (device["device_id"], device["org_id"], device["hostname"], running_config, datetime.utcnow().isoformat()))

                results["success"] += 1
                print(f"[BACKUP] ✅ {device['hostname']} — success")

            except Exception as e:
                cursor.execute("""
                    INSERT INTO config_backups (device_id, org_id, hostname, config_text, backup_type, status, error_message, created_at)
                    VALUES (?, ?, ?, '', 'scheduled', 'failed', ?, ?)
                """, (device["device_id"], device["org_id"], device["hostname"], str(e), datetime.utcnow().isoformat()))

                results["failed"] += 1
                results["errors"].append(f"{device['hostname']}: {e}")
                print(f"[BACKUP] ❌ {device['hostname']} — {e}")

        # Clean up old backups based on retention
        cursor.execute("SELECT DISTINCT org_id FROM devices")
        orgs = [row["org_id"] for row in cursor.fetchall()]
        for oid in orgs:
            try:
                cursor.execute("SELECT retention_days FROM backup_settings WHERE org_id = ?", (oid,))
                row = cursor.fetchone()
                retention = row["retention_days"] if row else 30
                cutoff = (datetime.utcnow() - timedelta(days=retention)).isoformat()
                cursor.execute("DELETE FROM config_backups WHERE org_id = ? AND created_at < ?", (oid, cutoff))
            except Exception:
                pass

        conn.commit()
        conn.close()

        print(f"[BACKUP COMPLETE] ✅ {results['success']} success | ❌ {results['failed']} failed")
        return results


def schedule_org_backup(app, org_id, frequency, hour, minute):
    """Schedule backup for a specific org."""
    job_id = f"backup_org_{org_id}"

    # Remove existing job if any
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass

    if frequency == "hourly":
        scheduler.add_job(func=run_backup, trigger="cron", minute=minute, args=[app, org_id], id=job_id, replace_existing=True)
        print(f"[SCHEDULER] ✅ Org {org_id}: Hourly backups at :{minute:02d}")
    elif frequency == "every_6_hours":
        scheduler.add_job(func=run_backup, trigger="cron", hour="0,6,12,18", minute=minute, args=[app, org_id], id=job_id, replace_existing=True)
        print(f"[SCHEDULER] ✅ Org {org_id}: Every 6 hours at :{minute:02d}")
    elif frequency == "every_12_hours":
        scheduler.add_job(func=run_backup, trigger="cron", hour="0,12", minute=minute, args=[app, org_id], id=job_id, replace_existing=True)
        print(f"[SCHEDULER] ✅ Org {org_id}: Every 12 hours at :{minute:02d}")
    elif frequency == "weekly":
        scheduler.add_job(func=run_backup, trigger="cron", day_of_week="sun", hour=hour, minute=minute, args=[app, org_id], id=job_id, replace_existing=True)
        print(f"[SCHEDULER] ✅ Org {org_id}: Weekly (Sunday) at {hour:02d}:{minute:02d}")
    else:  # daily (default)
        scheduler.add_job(func=run_backup, trigger="cron", hour=hour, minute=minute, args=[app, org_id], id=job_id, replace_existing=True)
        print(f"[SCHEDULER] ✅ Org {org_id}: Daily at {hour:02d}:{minute:02d}")


def start_scheduler(app):
    """Start scheduler and load all org backup schedules."""
    import sqlite3

    conn = sqlite3.connect("swytchai.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM backup_settings WHERE enabled = 1")
        settings = [dict(row) for row in cursor.fetchall()]
    except Exception:
        settings = []

    conn.close()

    if not scheduler.running:
        scheduler.start()

    for s in settings:
        schedule_org_backup(app, s["org_id"], s["frequency"], s["backup_hour"], s["backup_minute"])

    if not settings:
        print("[SCHEDULER] ✅ Started (no org schedules configured yet)")
    else:
        print(f"[SCHEDULER] ✅ Started with {len(settings)} org schedule(s)")


def run_backup_now(app, org_id=None):
    """Trigger an immediate backup."""
    return run_backup(app, org_id)