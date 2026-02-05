#!/usr/bin/env python
"""
Script to set up the Knowledge Base Synchronization cronjob

This script facilitates the installation of the sync_knowledge_base.py script as a cronjob
that will run daily at 3:00 AM. It must be executed with sufficient privileges
to modify the crontab.

The cronjob ensures that the AWS Bedrock Knowledge Base is automatically synchronized
after data updates, keeping the AI assistant responses up-to-date.

Usage:
    python setup_cron_kb_sync.py install   # Install the cronjob
    python setup_cron_kb_sync.py remove    # Remove the cronjob
    python setup_cron_kb_sync.py status    # Show cronjob status
"""

import os
import sys
import subprocess
from pathlib import Path
from crontab import CronTab

CURRENT_DIR = Path(__file__).resolve().parent
KB_SYNC_SCRIPT = CURRENT_DIR / "sync_knowledge_base.py"
PROJECT_ROOT = CURRENT_DIR.parent.parent.parent
LOG_DIR = PROJECT_ROOT / "data" / "logs"
CRON_COMMENT = "kb_sync_generator"
PYTHON_BIN = sys.executable

sys.path.append(str(PROJECT_ROOT))

from app.utils.logger.logger_util import get_logger
logger = get_logger()


def check_requirements():
    """Checks whether the necessary requirements are met to execute the script"""
    if not KB_SYNC_SCRIPT.exists():
        logger.error(f"❌ Error: sync_knowledge_base.py script not found at {KB_SYNC_SCRIPT}")
        return False
    
    try:
        os.chmod(KB_SYNC_SCRIPT, 0o755)
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
    log_file = LOG_DIR / "kb_sync.log"
    return f"{PYTHON_BIN} {KB_SYNC_SCRIPT} >> {log_file} 2>&1"


def install_cronjob():
    """Installs the Knowledge Base synchronization cronjob"""
    logger.info("🔧 Installing Knowledge Base synchronization cronjob...")
    
    if not check_requirements():
        return False
    
    try:
        cron = CronTab(user=True)
        
        cron.remove_all(comment=CRON_COMMENT)

        job = cron.new(command=get_cron_command(), comment=CRON_COMMENT)
        job.setall('0 4 * * 0')
        
        cron.write()
        
        logger.info("✅ Cronjob installed successfully!")
        logger.info(f"⏰ Schedule: Weekly on Sunday at 4:00 AM")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error installing cronjob: {e}")
        return False


def remove_cronjob():
    """Removes the Knowledge Base synchronization cronjob"""
    logger.info("🗑️  Removing Knowledge Base synchronization cronjob...")
    
    try:
        cron = CronTab(user=True)

        if cron.remove_all(comment=CRON_COMMENT):
            cron.write()
            logger.info(f"✅ Cronjob removed successfully!")
            return True
        else:
            logger.warning("⚠️  No cronjob found with the specified comment")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error removing cronjob: {e}")
        return False


def show_status():
    """Shows the current status of the Knowledge Base synchronization cronjob"""
    logger.info("📊 Checking Knowledge Base synchronization cronjob status...")
    
    try:
        cron = CronTab(user=True)
        jobs = list(cron.find_comment(CRON_COMMENT))
        
        if not jobs:
            logger.info("❌ Cronjob is NOT installed")
            return
        
        logger.info(f"✅ Cronjob is INSTALLED ({len(jobs)} job(s) found)")
        
        for job in jobs:
            logger.info(f"   Command: {job.command}")
            schedule = job.schedule()
            next_run = schedule.get_next()
            logger.info(f"   Next run: {next_run}")
        
    except Exception as e:
        logger.error(f"❌ Error when checking the cronjob status: {e}")


def test_script():
    if not check_requirements():
        return False
        
    logger.info("🧪 Running script in test mode...")
    try:
        result = subprocess.run([PYTHON_BIN, str(KB_SYNC_SCRIPT)], 
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
    """Prints usage instructions"""
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
        return 0 if install_cronjob() else 1
    elif command == "remove":
        return 0 if remove_cronjob() else 1
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