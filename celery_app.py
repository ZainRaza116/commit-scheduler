from celery import Celery
from celery.schedules import crontab
import pytz
import sys
import os
import random

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Celery('commit_scheduler')

# Redis configuration
app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    timezone='Asia/Karachi',
    enable_utc=True,
)

# Random scheduling: 1-4 times per day at random times
app.conf.beat_schedule = {
    'random-commit-1': {
        'task': 'celery_app.random_schedule_commits',
        'schedule': crontab(hour=10, minute=0),  # 10:00 AM - Morning slot
    },
    'random-commit-2': {
        'task': 'celery_app.random_schedule_commits', 
        'schedule': crontab(hour=14, minute=0),  # 2:00 PM - Afternoon slot
    },
    'random-commit-3': {
        'task': 'celery_app.random_schedule_commits',
        'schedule': crontab(hour=18, minute=0),  # 6:00 PM - Evening slot  
    },
    'random-commit-4': {
        'task': 'celery_app.random_schedule_commits',
        'schedule': crontab(hour=22, minute=0),  # 10:00 PM - Night slot
    },
}

@app.task
def random_schedule_commits():
    """Randomly decide whether to make commits (25-75% chance)"""
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Random chance to actually run (25-75% probability)
    should_run = random.random() < random.uniform(0.25, 0.75)
    
    if not should_run:
        logger.info("🎲 Random scheduler: Skipping this time slot")
        return {"skipped": True, "reason": "Random decision"}
    
    logger.info("🎲 Random scheduler: Executing commits now!")
    return make_commits()

@app.task  
def make_commits():
    """Celery task for making commits"""
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Celery task started - making commits")
    
    try:
        # Import here to avoid import issues
        from daily_commits import DynamicCodeModifier
        
        modifier = DynamicCodeModifier()
        results = modifier.run_dynamic_commits()
        
        successful = sum(1 for r in results.values() if r.get("success"))
        failed = len(results) - successful
        
        logger.info(f"✅ Celery task completed: {successful} successful, {failed} failed")
        return {"successful": successful, "failed": failed, "results": results}
        
    except Exception as e:
        logger.error(f"❌ Celery task failed: {e}")
        raise