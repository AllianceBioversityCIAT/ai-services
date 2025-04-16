#!/usr/bin/env python

import os
import sys
import time
import errno
import fcntl
import shutil
import signal
import lancedb
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))


from app.utils.config.config_util import MS_NAME
from app.utils.logger.logger_util import get_logger
from app.llm.vectorize import DB_PATH, TEMP_TABLE_NAME
from app.utils.notification.notification_service import NotificationService


LOCK_FILE = "/tmp/lancedb_cleaner.lock"
MAX_WAIT_TIME = 3600
WAIT_INTERVAL = 60
TEMP_DOCUMENTS_PATH = str(Path(DB_PATH) / f"{TEMP_TABLE_NAME}.lance")


logger = get_logger()
notification_service = NotificationService()


class LockError(Exception):
    pass


def acquire_lock():
    try:
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.lockf(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        logger.info("✅ Lock acquired successfully")
        return lock_fd
    except IOError as e:
        if e.errno == errno.EACCES or e.errno == errno.EAGAIN:
            logger.warning("⚠️ Could not acquire lock. Another instance of the script is running.")
            raise LockError("Another instance of the script is running")
        raise


def release_lock(lock_fd):
    try:
        fcntl.lockf(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()
        logger.info("✅ Lock released successfully")
    except Exception as e:
        logger.error(f"❌ Error releasing lock: {str(e)}")


def has_active_transactions():
    try:
        db = lancedb.connect(DB_PATH)
        
        if TEMP_TABLE_NAME not in db.table_names():
            logger.info("📊 Temporary table does not exist, no active transactions")
            return False
        
        transactions_path = Path(TEMP_DOCUMENTS_PATH) / "_transactions"

        if not transactions_path.exists():
            logger.info("📊 Transactions folder does not exist, no active transactions")
            return False
            
        transaction_files = list(transactions_path.glob("*.txn"))
        current_time = datetime.now()
        
        for txn_file in transaction_files:
            file_mtime = datetime.fromtimestamp(txn_file.stat().st_mtime)
            time_diff = current_time - file_mtime
            
            if time_diff < timedelta(minutes=5):
                logger.info(f"⚠️ Active transaction detected: {txn_file.name}, modified {time_diff} ago")
                return True
                
        logger.info(f"📊 {len(transaction_files)} old transaction(s) found, none active")
        return False
        
    except Exception as e:
        logger.error(f"❌ Error checking transactions: {str(e)}")
        return True


def remove_temp_documents():
    try:
        if not Path(TEMP_DOCUMENTS_PATH).exists():
            logger.info(f"🔍 Folder {TEMP_DOCUMENTS_PATH} does not exist, nothing to delete")
            return True
            
        logger.info(f"🗑️ Deleting temporary documents folder: {TEMP_DOCUMENTS_PATH}")
        shutil.rmtree(TEMP_DOCUMENTS_PATH)
        logger.info("✅ Folder deleted successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Error deleting folder: {str(e)}")
        return False


async def send_notification(success, error_msg=None):
    if success:
        await notification_service.send_slack_notification(
            emoji="🧹",
            app_name=MS_NAME,
            color="#36a64f",
            title="LanceDB Cleanup Completed",
            message=f"Successfully deleted the temporary documents folder",
            priority="Low",
            time_taken=None
        )
    else:
        await notification_service.send_slack_notification(
            emoji="⚠️",
            app_name=MS_NAME,
            color="#FF0000",
            title="Error in LanceDB Cleanup",
            message=f"Error cleaning the temporary documents folder: {error_msg}",
            priority="High",
            time_taken=None
        )


def handle_timeout(signum, frame):
    logger.error("🛑 Cleanup skipped due to persistent active transactions")
    raise TimeoutError("Timeout waiting for transactions to complete")


def main():
    lock_fd = None
    start_time = time.time()
    success = False
    error_msg = None
    
    logger.info("🚀 Starting LanceDB cleanup script")
    
    try:
        lock_fd = acquire_lock()
        
        signal.signal(signal.SIGALRM, handle_timeout)
        signal.alarm(MAX_WAIT_TIME)
        
        total_wait_time = 0
        while has_active_transactions() and total_wait_time < MAX_WAIT_TIME:
            wait_time = min(WAIT_INTERVAL, MAX_WAIT_TIME - total_wait_time)
            logger.info(f"⏳ Waiting {wait_time} seconds for active transactions to complete...")
            time.sleep(wait_time)
            total_wait_time += wait_time
        
        if total_wait_time >= MAX_WAIT_TIME:
            logger.warning("⚠️ Maximum wait time exceeded")
        
        success = remove_temp_documents()
        signal.alarm(0)
        
    except LockError as e:
        logger.info(f"ℹ️ {str(e)}")
        error_msg = str(e)
    except TimeoutError as e:
        logger.error(f"❌ {str(e)}")
        error_msg = str(e)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        error_msg = str(e)
    finally:
        if lock_fd:
            release_lock(lock_fd)
        
        execution_time = time.time() - start_time
        logger.info(f"⏱️ Total execution time: {execution_time:.2f} seconds")
        
        try:
            import asyncio
            asyncio.run(send_notification(success, error_msg))
        except Exception as e:
            logger.error(f"❌ Error sending notification: {str(e)}")
        
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())