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
        
        # Create connection without context manager
        connection = routeros_api.RouterOsApiPool(
            ip_router,
            username=f'{component.username}',
            password=f'{component.password}',
            plaintext_login=True
        )
        api = connection.get_api()

        try:
            #######################
            #### KICK PROCESS #####
            collect = api.get_resource('/interface/pppoe-server')

            #### COMMAND TO GET ID INTERFACE PPPOE-xx FROM ROUTER
            get_id_user_get_id = collect.get(user=user_nya_pppoe)
            id_user_pppoe = [id["id"] for id in get_id_user_get_id]
            iget_id_user = id_user_pppoe[0]
            collect.remove(id=iget_id_user)
            sleep(0.5)  # Reduced from 1 second
            traffic_device[ip_router], interface_rb[ip_router] = get_traffic(api)

            into_db_user(traffic_device, "kick")
            logging.info(f"User '{user_nya_pppoe}' kicked successfully")
            return f"success_{user_nya_pppoe}", 200

        finally:
            # Ensure connection is always closed
            connection.disconnect()

    except exceptions.RouterOsApiConnectionError as e:
        logging.error(f"Connection error: {e}")
        return e, 500
    except exceptions.RouterOsApiCommunicationError as e:
        logging.error(f"Communication error: {e}")
        return e, 400
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return str(e), 500




