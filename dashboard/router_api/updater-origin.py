from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from router_api import collect


def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(collect.get_rb, 'interval', minutes=10)
    scheduler.start()  
