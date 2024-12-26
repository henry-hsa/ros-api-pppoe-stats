from time import sleep
import routeros_api
from routeros_api import exceptions
import re
from monitor_app.models import Devices, UserInfo
from datetime import datetime
from router_api.collect import get_traffic
from router_api.save_db import into_db_user
import routeros_api


def kick(ip_router,user_nya_pppoe):

    try:
        traffic_device = {}
        interface_rb = {}

        component = Devices.objects.filter(router_ip=ip_router).first()
        username = component.username
        password = component.password
        connection = routeros_api.RouterOsApiPool(ip_router, username=f'{username}', password=f'{password}', plaintext_login=True)
        api = connection.get_api()

        #######################
        #### KICK PROCESS #####
        collect = api.get_resource('/interface/pppoe-server')

        #### COMMAND TO GET ID INTERFACE PPPOE-xx FROM ROUTER
        get_id_user_get_id = collect.get(user=user_nya_pppoe)
        id_user_pppoe = [id["id"] for id in get_id_user_get_id]
        iget_id_user = id_user_pppoe[0]
        collect.remove(id=iget_id_user)
        sleep(1)
        traffic_device[ip_router], interface_rb[ip_router] = get_traffic(api)

        connection.disconnect()


        into_db_user(traffic_device,"kick")
        return f"success_{user_nya_pppoe}",200
    except exceptions.RouterOsApiConnectionError as e:
        print(e)
        return e,500
    except exceptions.RouterOsApiCommunicationError as e:
        print(e)
        return e,400
