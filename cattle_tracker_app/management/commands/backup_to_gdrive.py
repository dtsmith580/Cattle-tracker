import os
import datetime
import subprocess
from django.core.management.base import BaseCommand
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

class Command(BaseCommand):
    help = 'Backs up the PostgreSQL database and uploads it to Google Drive'

    def handle(self, *args, **kwargs):
        # Set your backup file path and name
        now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"C:\\temp\\cattle_tracker_backup_{now}.sql"
        # Replace these values as needed:
        dbname = 'cattle_tracker'
        dbuser = 'cattle_user'
        dbhost = '127.0.0.1'
        dbport = '5433'

        # Dump the database
        dump_cmd = f'pg_dump -U {dbuser} -h {dbhost} -p {dbport} -F p -f "{backup_path}" {dbname}'
        print(f"Running: {dump_cmd}")
        env = os.environ.copy()
        env["PGPASSWORD"] = os.environ.get("PGPASSWORD", "")  # set this in your environment
        subprocess.run(dump_cmd, shell=True, env=env, check=True)
        print(f"Database backup created at {backup_path}")

        # Authenticate and upload to Google Drive
        gauth = GoogleAuth()
        # First run will open browser for Google auth—follow instructions.
        gauth.LocalWebserverAuth()
        drive = GoogleDrive(gauth)
        file1 = drive.CreateFile({'title': os.path.basename(backup_path)})
        file1.SetContentFile(backup_path)
        file1.Upload()
        print('Backup uploaded to Google Drive!')

        # (Optional) Delete local backup
        os.remove(backup_path)
        print('Local backup deleted.')
