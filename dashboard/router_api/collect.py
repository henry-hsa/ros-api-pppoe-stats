import logging
from monitor_app.models import Devices
import routeros_api
from routeros_api import exceptions
import re
from datetime import datetime
from collections import Counter
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from .shared_utils import handle_router_error
from .save_db import (
    into_db_resource, 
    into_db_user, 
    into_db_interface, 
    into_db_traffic_agg, 
    into_db_user_traffic_accumulate
)


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


def process_single_device(device_info, shared_data):
    ip = device_info.router_ip
    username = device_info.username
    password = device_info.password
    router_name = device_info.router_name
    
    logging.info(f"Starting connection to {router_name} ({ip})")
    try:
        connection = routeros_api.RouterOsApiPool(
            ip, 
            username=f'{username}', 
            password=f'{password}', 
            plaintext_login=True
        )
        api = connection.get_api()
        
        with shared_data['lock']:
            logging.debug(f"Collecting resource info for {ip}")
            shared_data['resource_device'][ip] = get_info(api)
            
            logging.debug(f"Collecting traffic info for {ip}")
            shared_data['traffic_device'][ip], shared_data['interface_rb'][ip] = get_traffic(api)
            
            logging.debug(f"Collecting traffic aggregation for {ip}")
            shared_data['traffic_agg'][ip] = get_traffic_agg(api)
            
        connection.disconnect()
        logging.info(f"Successfully processed device {router_name} ({ip})")
        
    except exceptions.RouterOsApiConnectionError as e:
        logging.error(f"Connection error for {ip}: {str(e)}")
        item_save = TrafficAgg(
            router_ip=ip,
            router_name=router_name,
            upload="null",
            download="null",
            cpu_load="null"
        )
        item_save.save()
    except Exception as e:
        logging.error(f"Unexpected error processing {ip}: {str(e)}")
        raise


def get_rb():
    logging.info("Starting collection cycle")
    
    try:
        device = Devices.objects.all()
        device_count = len(device)
        logging.info(f"Found {device_count} devices in database")
        
        if (device_count == 0):
            logging.error("No devices found in database!")
            return
            
        shared_data = {
            'resource_device': {},
            'traffic_device': {},
            'interface_rb': {},
            'traffic_agg': {},
            'lock': Lock()
        }
        
        now = datetime.today()
        logging.info(f"Collection started at: {now}")

        # Log device details before processing
        for d in device:
            logging.info(f"Will process device: {d.router_name} ({d.router_ip})")

        # Use ThreadPoolExecutor to process devices in parallel
        max_workers = min(device_count, 5)  # Reduce concurrency to 5 threads
        logging.info(f"Using {max_workers} worker threads")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(
                lambda x: process_single_device(x, shared_data), 
                device
            )

        # Verify collected data
        logging.info(f"Devices processed: {len(shared_data['resource_device'])}")
        logging.info(f"Traffic data collected: {len(shared_data['traffic_device'])}")
        logging.info(f"Interface data collected: {len(shared_data['interface_rb'])}")
        logging.info(f"Traffic aggregation collected: {len(shared_data['traffic_agg'])}")

        # Use collected data from shared dictionary
        logging.info("In Progress, Starting to insert collected data to database")
        into_db_resource(shared_data['resource_device'])
        into_db_user(shared_data['traffic_device'], "update_interval")
        into_db_interface(shared_data['interface_rb'])
        into_db_traffic_agg(shared_data['traffic_agg'], shared_data['resource_device'])
        into_db_user_traffic_accumulate(shared_data['traffic_device'], "update_interval")
        logging.info("Collection cycle completed successfully")

    except Exception as e:
        logging.error(f"Critical error in get_rb: {str(e)}")
        raise


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

            uptime = i.get("uptime", "unknown")
            service = i.get("service", "unknown")
            remote_address = i.get("remote-address", "unknown")
            ipaddress = active_user.get(user, "unknown")
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
                # Updated regex to handle more PPPoE interface name formats
                user_profile = re.search(r"(?:^<pppoe-(\d+)>$|^pppoe-(\d+)$|^pppoe-in(\d+)$)", name)
                if user_profile is None:
                    logging.debug(f"Skipping interface with unmatched format: {name}")
                    continue
                    
                # Get the first non-None group
                info_user = next((g for g in user_profile.groups() if g is not None), None)
                
                if not info_user:
                    logging.debug(f"No user ID found in interface name: {name}")
                    continue

                if info_user in user_info:

                    all_user_info = ";".join(user_info[info_user])
                    interface_name = name
                else:
                    logging.debug(f"User {info_user} not found in user_info for interface {name}")
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

