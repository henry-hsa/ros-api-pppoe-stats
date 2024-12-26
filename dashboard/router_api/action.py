import logging
from time import sleep
import routeros_api
from routeros_api import exceptions
import re
from monitor_app.models import Devices, UserInfo
from datetime import datetime
from router_api.collect import get_traffic
from router_api.save_db import into_db_user


def kick(ip_router, user_nya_pppoe):
    """
    Disconnect the specified PPPoE user and update the database.
    """
    logging.info(f"Attempting to kick user '{user_nya_pppoe}' on router '{ip_router}'")
    try:
        traffic_device = {}
        interface_rb = {}
        component = Devices.objects.filter(router_ip=ip_router).first()
        
        if not component:
            msg = f"Router {ip_router} not found"
            logging.error(msg)
            return msg, 404

        # Create connection without context manager
        connection = routeros_api.RouterOsApiPool(
            ip_router,
            username=f'{component.username}',
            password=f'{component.password}',
            plaintext_login=True
        )
        api = connection.get_api()

        try:
            collect = api.get_resource('/interface/pppoe-server')

            # Get user interface and check if exists
            get_id_user_get_id = collect.get(user=user_nya_pppoe)
            if not get_id_user_get_id:
                msg = f"User {user_nya_pppoe} not found on router {ip_router}"
                logging.warning(msg)
                return msg, 404

            # Extract ID and kick user
            id_user_pppoe = [id["id"] for id in get_id_user_get_id]
            if not id_user_pppoe:
                msg = f"No valid interface ID found for user {user_nya_pppoe}"
                logging.warning(msg)
                return msg, 404

            collect.remove(id=id_user_pppoe[0])
            sleep(1)  
            
            # Update traffic info
            traffic_info = get_traffic(api)
            if traffic_info and traffic_info[0]:  # Check if get_traffic returned valid data
                traffic_device[ip_router], interface_rb[ip_router] = traffic_info
                into_db_user(traffic_device, "kick")
            
            logging.info(f"User '{user_nya_pppoe}' kicked successfully")
            return f"success_{user_nya_pppoe}", 200

        finally:
            connection.disconnect()

    except exceptions.RouterOsApiConnectionError as e:
        msg = f"Connection error: {str(e)}"
        logging.error(msg)
        return msg, 500
    except exceptions.RouterOsApiCommunicationError as e:
        msg = f"Communication error: {str(e)}"
        logging.error(msg)
        return msg, 400
    except Exception as e:
        msg = f"Unexpected error: {str(e)}"
        logging.error(msg)
        return msg, 500




