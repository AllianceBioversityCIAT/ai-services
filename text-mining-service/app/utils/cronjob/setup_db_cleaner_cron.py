#!/usr/bin/env python
"""
Script to set up the LanceDB cleanup cronjob

This script facilitates the installation of the db_cleaner.py script as a cronjob
that will run daily at midnight. It must be executed with sufficient privileges
to modify the crontab.

Usage:
    python setup_db_cleaner_cron.py install   # Install the cronjob
    python setup_db_cleaner_cron.py remove    # Remove the cronjob
    python setup_db_cleaner_cron.py status    # Show cronjob status
"""

import os
import sys
import subprocess
from pathlib import Path
from crontab import CronTab


CURRENT_DIR = Path(__file__).resolve().parent
DB_CLEANER_SCRIPT = CURRENT_DIR / "db_cleaner.py"
PROJECT_ROOT = CURRENT_DIR.parent.parent.parent
LOG_DIR = PROJECT_ROOT / "data" / "logs"
CRON_COMMENT = "lancedb_cleaner"
PYTHON_BIN = sys.executable


def check_requirements():
    """Checks whether the necessary requirements are met to execute the script"""
    if not DB_CLEANER_SCRIPT.exists():
        print(f"❌ Error: db_cleaner.py script not found at {DB_CLEANER_SCRIPT}")
        return False
    
    try:
        os.chmod(DB_CLEANER_SCRIPT, 0o755)
    except Exception as e:
        print(f"⚠️ Warning: Failed to make script executable: {e}")
    
    if not LOG_DIR.exists():
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            print(f"✅ Log directory created: {LOG_DIR}")
        except Exception as e:
            print(f"❌ Error: Failed to create log directory: {e}")
            return False
    
    return True


def get_cron_command():
    """Generates the cron command using absolute paths for better reliability"""
    log_file = LOG_DIR / "db_cleaner_cron.log"
    return f"{PYTHON_BIN} {DB_CLEANER_SCRIPT} >> {log_file} 2>&1"


def install_cron():
    """Installs the cronjob to run the script daily at 7:00 PM"""
    if not check_requirements():
        return False
    
    try:
        cron = CronTab(user=True)
        
        cron.remove_all(comment=CRON_COMMENT)
        
        job = cron.new(command=get_cron_command(), comment=CRON_COMMENT)
        job.setall('0 1 * * *')
        
        cron.write()
        
        print(f"✅ Cronjob successfully installed.")
        print(f"   Command: {job.command}")
        print(f"   Schedule: {job.slices}")
        return True
        
    except Exception as e:
        print(f"❌ Error installing cronjob: {e}")
        return False


def remove_cron():
    """Removes the LanceDB cleanup cronjob"""
    try:
        cron = CronTab(user=True)
        
        if cron.remove_all(comment=CRON_COMMENT):
            cron.write()
            print("✅ Cronjob successfully removed.")
            return True
        else:
            print("ℹ️ No cronjob found to remove.")
            return False
            
    except Exception as e:
        print(f"❌ Error deleting cronjob: {e}")
        return False


def show_status():
    """Displays the current status of the cronjob"""
    try:
        cron = CronTab(user=True)
        jobs = list(cron.find_comment(CRON_COMMENT))
        
        if not jobs:
            print("ℹ️ No cronjob installed for LanceDB cleanup.")
            return
            
        print(f"✅ Cronjob configurado para la limpieza de LanceDB:")
        for job in jobs:
            print(f"   Command: {job.command}")
            schedule = job.schedule(date_from=job.next())
            next_run = schedule.get_next()
            print(f"   Next run: {next_run}")
            
    except Exception as e:
        print(f"❌ Error when checking the cronjob status: {e}")


def test_script():
    """Runs the cleanup script in test mode"""
    if not check_requirements():
        return False
        
    print(f"🧪 Running db_cleaner.py script in test mode...")
    try:
        result = subprocess.run([PYTHON_BIN, str(DB_CLEANER_SCRIPT)], 
                               capture_output=True, text=True)
        
        print("\n--- SCRIPT OUTPUT ---")
        print(result.stdout)
        
        if result.stderr:
            print("\n--- ERRORS ---")
            print(result.stderr)
            
        print(f"\n✅ Script executed with exit code: {result.returncode}")
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error executing the script: {e}")
        return False


def print_usage():
    """Displays the help message"""
    print(f"""
  Usage: {sys.argv[0]} <command>

  Available commands:
    install   - Install the cronjob to run the script daily at midnight
    remove    - Remove the cronjob
    status    - Show the current status of the cronjob
    test      - Run the db_cleaner.py script in test mode
    help      - Show this help message
""")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print_usage()
        return 1
        
    command = sys.argv[1].lower()
    
    if command == "install":
        return 0 if install_cron() else 1
    elif command == "remove":
        return 0 if remove_cron() else 1
    elif command == "status":
        show_status()
        return 0
    elif command == "test":
        return 0 if test_script() else 1
    elif command in ["help", "-h", "--help"]:
        print_usage()
        return 0
    else:
        print(f"❌ Unknown command: {command}")
        print_usage()
        return 1


if __name__ == "__main__":
    sys.exit(main())