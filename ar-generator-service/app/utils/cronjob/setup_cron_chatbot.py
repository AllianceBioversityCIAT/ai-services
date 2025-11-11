#!/usr/bin/env python
"""
Script to set up the Weekly Chatbot Data Update cronjob

This script facilitates the installation of the update_chatbot_data.py script as a cronjob
that will run weekly on Sundays at 1:00 AM. It must be executed with sufficient privileges
to modify the crontab.

Usage:
    python setup_cron_chatbot.py install   # Install the cronjob
    python setup_cron_chatbot.py remove    # Remove the cronjob
    python setup_cron_chatbot.py status    # Show cronjob status
"""

import os
import sys
import subprocess
from pathlib import Path
from crontab import CronTab

CURRENT_DIR = Path(__file__).resolve().parent
CHATBOT_SCRIPT = CURRENT_DIR / "update_chatbot_data.py"
PROJECT_ROOT = CURRENT_DIR.parent.parent.parent
LOG_DIR = PROJECT_ROOT / "data" / "logs"
CRON_COMMENT = "chatbot_data_updater"
PYTHON_BIN = sys.executable

sys.path.append(str(PROJECT_ROOT))

from app.utils.logger.logger_util import get_logger
logger = get_logger()


def check_requirements():
    """Checks whether the necessary requirements are met to execute the script"""
    if not CHATBOT_SCRIPT.exists():
        logger.error(f"❌ Error: update_chatbot_data.py script not found at {CHATBOT_SCRIPT}")
        return False
    
    try:
        os.chmod(CHATBOT_SCRIPT, 0o755)
    except Exception as e:
        logger.warning(f"⚠️ Warning: Failed to make script executable: {e}")
    
    if not LOG_DIR.exists():
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Log directory created: {LOG_DIR}")
        except Exception as e:
            logger.error(f"❌ Error: Failed to create log directory: {e}")
            return False
    
    return True


def get_cron_command():
    """Generates the cron command using absolute paths for better reliability"""
    log_file = LOG_DIR / "chatbot_data_cron.log"
    return f"{PYTHON_BIN} {CHATBOT_SCRIPT} >> {log_file} 2>&1"


def install_cron():
    """Installs the cronjob to run the script weekly on Sundays at 1:00 AM"""
    if not check_requirements():
        return False
    
    try:
        cron = CronTab(user=True)
        
        cron.remove_all(comment=CRON_COMMENT)
        
        job = cron.new(command=get_cron_command(), comment=CRON_COMMENT)
        job.setall('0 3 * * 0')  # Weekly on Sunday at 3:00 AM (1 hour before AR generator)
        
        cron.write()
        
        logger.info("✅ Cronjob successfully installed")
        logger.info(f"   Command: {job.command}")
        logger.info(f"   Schedule: {job.slices}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error installing cronjob: {e}")
        return False


def remove_cron():
    """Removes the Chatbot Data Update cronjob"""
    try:
        cron = CronTab(user=True)
        
        if cron.remove_all(comment=CRON_COMMENT):
            cron.write()
            logger.info("✅ Cronjob successfully removed")
            return True
        else:
            logger.info("ℹ️  No cronjob found to remove")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error deleting cronjob: {e}")
        return False


def show_status():
    """Displays the current status of the cronjob"""
    try:
        cron = CronTab(user=True)
        jobs = list(cron.find_comment(CRON_COMMENT))
        
        if not jobs:
            logger.info("ℹ️  No cronjob installed for Chatbot Data Update")
            return
            
        logger.info("✅ Cronjob configured for Chatbot Data Update:")
        for job in jobs:
            logger.info(f"   Command: {job.command}")
            schedule = job.schedule()
            next_run = schedule.get_next()
            logger.info(f"   Next run: {next_run}")
            
    except Exception as e:
        logger.error(f"❌ Error when checking the cronjob status: {e}")


def test_script():
    """Runs the chatbot data update script in test mode"""
    if not check_requirements():
        return False
        
    logger.info("🧪 Running update_chatbot_data.py script in test mode...")
    try:
        result = subprocess.run([PYTHON_BIN, str(CHATBOT_SCRIPT)], 
                               capture_output=True, text=True)
        
        logger.info("\n--- SCRIPT OUTPUT ---")
        logger.info(result.stdout)
        
        if result.stderr:
            logger.error("\n--- ERRORS ---")
            logger.error(result.stderr)
            
        logger.info(f"\n✅ Script executed with exit code: {result.returncode}")
        return result.returncode == 0
        
    except Exception as e:
        logger.error(f"❌ Error executing the script: {e}")
        return False


def print_usage():
    """Displays the help message"""
    logger.info(f"""
  Usage: {sys.argv[0]} <command>

  Available commands:
    install   - Install the cronjob to run the script weekly on Sundays at 1:00 AM
    remove    - Remove the cronjob
    status    - Show the current status of the cronjob
    test      - Run the update_chatbot_data.py script in test mode
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
        logger.error(f"❌ Unknown command: {command}")
        print_usage()
        return 1


if __name__ == "__main__":
    sys.exit(main())