from monitor_app.models import Devices, DevicesInfo, UserInfo, ListInterface, TrafficAgg
import routeros_api
from routeros_api import exceptions
import re
from datetime import datetime
from collections import Counter
from router_api.save_db import into_db_resource, into_db_user, into_db_interface, into_db_traffic_agg, into_db_user_traffic_accumulate


def convert_bytes(bytes_number):
    tags = ["Bits", "Kb", "Mb", "Gb", "Tb"]

    i = 0
    double_bytes = bytes_number

    while (i < len(tags) and bytes_number >= 1024):
        double_bytes = bytes_number / 1024.0
        i = i + 1
        bytes_number = bytes_number / 1024

    return str(round(double_bytes, 2)) + " " + tags[i]


def convert_bytes_only(bytes_number):
    tags = ["Bits", "Kb", "Mb", "Gb", "Tb"]

    i = 0
    double_bytes = bytes_number

    while (i < len(tags) and bytes_number >= 1024):
        double_bytes = bytes_number / 1024.0
        i = i + 1
        bytes_number = bytes_number / 1024

    return round(double_bytes, 2), tags[i]


def get_rb():
    resource_device = {}
    traffic_device = {}
    interface_rb = {}
    traffic_agg = {}
    device = Devices.objects.all()
    now = datetime.today()

    print(now)

    for ii in device:
        ip = ii.router_ip
        username = ii.username
        password = ii.password
        router_name = ii.router_name
        try:
            connection = routeros_api.RouterOsApiPool(
                ip, username=f'{username}', password=f'{password}', plaintext_login=True)
            api = connection.get_api()
            resource_device[ip] = get_info(api)
            traffic_device[ip], interface_rb[ip] = get_traffic(api)
            traffic_agg[ip] = get_traffic_agg(api)

            connection.disconnect()

        except exceptions.RouterOsApiConnectionError as e:
            print(e)
            item_save = TrafficAgg(
                router_ip=ip,
                router_name=router_name,
                upload="null",
                download="null",
                cpu_load="null"
            )
            item_save.save()

    try:
        ###################################
        #### INSERT To Tabel DevicesInfo ##
        ###################################
        into_db_resource(resource_device)

        #################################
        #### INSERT To Tabel UsersInfo ##
        #################################
        into_db_user(traffic_device, "update_interval")

        ###################################
        ### INSERT To Tabel ListInteface ##
        ###################################
        into_db_interface(interface_rb)

        ##################################
        #### INSERT To Tabel TrafficAgg ##
        ##################################
        into_db_traffic_agg(traffic_agg, resource_device)   
        into_db_user_traffic_accumulate(traffic_device, "update_interval")

    except exceptions.RouterOsApiCommunicationError as e:
        print(e)


def get_traffic_agg(api):
    try:
        monitor_traffic = api.get_binary_resource(
            '/interface').call('monitor-traffic', {'interface': b'aggregate', 'once': b''})
        ftx = monitor_traffic[0]['tx-bits-per-second']
        frx = monitor_traffic[0]['rx-bits-per-second']
        upload = ftx.decode()
        download = frx.decode()

        return f"{upload};{download}"

    except exceptions.RouterOsApiCommunicationError as e:
        print(e)


def get_info(api):
    try:
        resource_rb = []
        resources = api.get_resource('system/resource')
        identity = api.get_resource('system/identity')
        serial = api.get_resource('system/routerboard')
        serial_number = [serial_num["serial-number"]
                         for serial_num in serial.get()]
        show_info_rb = resources.get()
        name_identity = [iden["name"] for iden in identity.get()]

        for info in show_info_rb:
            uptime = info["uptime"]
            routerOS = info["version"]
            load_cpu = info["cpu-load"]
            router_type = info["board-name"]
            total_memory = int(info["total-memory"])
            free_memory = int(info["free-memory"])
            memory_usg = total_memory - free_memory
            memory_usage = convert_bytes(memory_usg)

            resource_rb.append(
                f"{name_identity[0]};{router_type};{uptime};{memory_usage};{load_cpu}%;{routerOS};{serial_number[0]}")

        return resource_rb

    except exceptions.RouterOsApiCommunicationError as e:
        print(e)


def get_traffic(api):
    user_info = {}
    active_user = {}
    all_user_pppoe = []
    all_int_vlan = []
    try:

        identity = api.get_resource('system/identity')
        name_identity = [iden["name"] for iden in identity.get()]

        #################################
        ##### GET USER IP PPPOE INFO ####
        #################################
        list_active = api.get_resource('ppp/active')
        show_list_active = list_active.get()

        # user check for kick user
        user_check = [i["name"] for i in show_list_active]

        for active in show_list_active:
            user_active = active["name"]
            ip_active = active["address"]
            active_user[user_active] = ip_active

        ##############################
        ##### GET USER PPPOE INFO ####
        ##############################
        list_user = api.get_resource('interface/pppoe-server')
        show_data_user = list_user.get()

        for i in show_data_user:
            user = i["user"]

            # CHECK IF USER NOT IN ACTIVE USER -> CONTINUE
            if not user in user_check:
                continue

            uptime = i["uptime"]
            service = i["service"]
            remote_address = i["remote-address"]
            ipaddress = active_user[user]
            item = [user, uptime, service, ipaddress, remote_address]
            user_info[user] = item

        list_interface = api.get_resource('interface')
        show_data = list_interface.get()

        ##############################
        ##### GET TX/RX BYTE INFO ####
        ##############################
        # print("Interface_name;User;Uptime;Service;IPAddress_remote;Remote_address;rx_byte;tx_byte")
        for interface in show_data:
            name = interface["name"]
            type_int = interface["type"]

            if re.match("^pppoe\-in$", type_int):
                user_profile = re.search("^\<pppoe\-(.*?)\>", name)
                info_user = user_profile.group(1)

                if info_user in user_info:

                    all_user_info = ";".join(user_info[info_user])
                    interface_name = name
                else:
                    continue
                rx_bytes = int(interface["rx-byte"])
                tx_bytes = int(interface["tx-byte"])

                all_user_pppoe.append(
                    f"{all_user_info};{rx_bytes};{tx_bytes};{interface_name};{name_identity[0]}")
            if re.match("^vlan$", type_int) or re.match("^ether$", type_int):
                mac_add = interface["mac-address"]
                all_int_vlan.append(
                    f"{name};{name_identity[0]};{type_int};{mac_add}")

            else:
                continue

        return all_user_pppoe, all_int_vlan
    except exceptions.RouterOsApiCommunicationError as e:
        print(e)
