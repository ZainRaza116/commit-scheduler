#!/usr/bin/env python3
"""
Automatic Scheduler for Dynamic Commits
Runs at 9:15 PM Pakistani Time Daily
"""

import schedule
import time
import logging
import json
from datetime import datetime
import pytz
from pathlib import Path
from daily_commits import DynamicCodeModifier

def setup_logging():
    """Setup logging for scheduler"""
    log_dir = Path.home() / ".local" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "scheduler.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def run_commits():
    """Run the commit process"""
    logger = setup_logging()
    pakistan_tz = pytz.timezone('Asia/Karachi')
    current_time = datetime.now(pakistan_tz)
    
    logger.info(f"🚀 Automatic commit scheduler triggered at {current_time.strftime('%Y-%m-%d %H:%M:%S')} PKT")
    
    try:
        modifier = DynamicCodeModifier()
        results = modifier.run_dynamic_commits()
        
        successful = sum(1 for r in results.values() if r.get("success"))
        failed = len(results) - successful
        
        logger.info(f"✅ Summary: {successful} successful commits, {failed} failed")
        
        # Log details for each repo
        for repo, result in results.items():
            repo_name = repo.split('/')[-1]  # Get just the folder name
            if result.get("success"):
                logger.info(f"  ✅ {repo_name}: {result.get('message', 'Success')}")
            else:
                logger.error(f"  ❌ {repo_name}: {result.get('error', 'Failed')}")
                
    except Exception as e:
        logger.error(f"💥 Scheduler error: {e}")

def main():
    """Main scheduler function"""
    logger = setup_logging()
    logger.info("🎯 Starting automatic commit scheduler...")
    logger.info("📅 Scheduled for 9:15 PM Pakistani Time (daily)")
    
    # Schedule for 9:15 PM Pakistani time every day
    schedule.every().day.at("21:30").do(run_commits)
    
    logger.info("⏰ Scheduler is now running automatically...")
    logger.info("💡 Logs will be saved to ~/.local/logs/scheduler.log")
    logger.info("🛑 Press Ctrl+C to stop")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()