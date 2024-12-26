import logging

def setup_logging(log_file):
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def handle_router_error(router_ip, router_name):
    """Handle router connection errors"""
    from monitor_app.models import TrafficAgg
    item_save = TrafficAgg(
        router_ip=router_ip,
        router_name=router_name,
        upload="null",
        download="null",
        cpu_load="null"
    )
    item_save.save()
