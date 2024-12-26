import os
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from .shared_utils import setup_logging
from . import collect

# Create logs directory
log_directory = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(log_directory, exist_ok=True)
log_file = os.path.join(log_directory, 'router_collection.log')

# Configure logging
setup_logging(log_file)

def start():
    try:
        scheduler = BackgroundScheduler()
        scheduler.add_job(collect.get_rb, 'interval', minutes=10)
        logging.info("Scheduler started with 10-minute interval")
        scheduler.start()
    except Exception as e:
        logging.error(f"Error starting scheduler: {str(e)}")
        raise