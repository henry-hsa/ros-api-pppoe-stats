import logging
from monitor_app.models import Devices, DevicesInfo, UserInfo, ListInterface, TrafficAgg
import routeros_api
from routeros_api import exceptions
import re
from datetime import datetime, timedelta
from collections import Counter
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import concurrent.futures
import time
from .shared_utils import handle_router_error
from .save_db import (
    into_db_resource, 
    into_db_user, 
    into_db_interface, 
    into_db_traffic_agg, 
    into_db_user_traffic_accumulate
)
import socket


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
    """Process single device with retry mechanism"""
    ip = device_info.router_ip
    max_retries = 2
    retry_delay = 1
    start_time = time.time()
    
    for attempt in range(max_retries):
        try:
            # Default socket timeout for underlying connections
            socket.setdefaulttimeout(10)  # 10 seconds timeout
            
            connection = routeros_api.RouterOsApiPool(
                ip, 
                username=f'{device_info.username}', 
                password=f'{device_info.password}', 
                plaintext_login=True
            )
            api = connection.get_api()
        
            with shared_data['lock']:
                logging.debug(f"Collecting resource info for {ip}")
                resource_info = get_info(api)
                if resource_info:
                    shared_data['resource_device'][ip] = resource_info
                
                logging.debug(f"Collecting traffic info for {ip}")
                traffic_info, interface_info = get_traffic(api)
                if traffic_info is not None:
                    shared_data['traffic_device'][ip] = traffic_info
                    shared_data['interface_rb'][ip] = interface_info
                
                logging.debug(f"Collecting traffic aggregation for {ip}")
                traffic_agg_info = get_traffic_agg(api)
                if traffic_agg_info:
                    shared_data['traffic_agg'][ip] = traffic_agg_info
                
            connection.disconnect()
            elapsed = time.time() - start_time
            logging.info(f"Device {device_info.router_name} ({ip}) processed in {elapsed:.2f} seconds")
            shared_data['timings'][ip] = elapsed
            break
        
        except (exceptions.RouterOsApiConnectionError, socket.timeout) as e:
            if attempt < max_retries - 1:
                logging.warning(f"Retry {attempt + 1} for {ip}: {str(e)}")
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                continue
            logging.error(f"All retries failed for {ip}: {str(e)}")
            handle_router_error(ip, device_info.router_name)
            elapsed = time.time() - start_time
            shared_data['timings'][ip] = elapsed
        except Exception as e:
            logging.error(f"Unexpected error for {ip}: {str(e)}")
            handle_router_error(ip, device_info.router_name)
            elapsed = time.time() - start_time
            shared_data['timings'][ip] = elapsed
            break
        finally:
            # Reset socket timeout to default
            socket.setdefaulttimeout(None)


def get_rb():
    logging.info("Starting collection cycle")
    
    try:
        collection_start = time.time()
        max_execution_time = 45  # seconds (less than scheduler interval)
        
        devices = list(Devices.objects.all())  # Convert QuerySet to list
        device_count = len(devices)
        logging.info(f"Found {device_count} devices in database")
        
        if (device_count == 0):
            logging.error("No devices found in database!")
            return
            
        shared_data = {
            'resource_device': {},
            'traffic_device': {},
            'interface_rb': {},
            'traffic_agg': {},
            'lock': Lock(),
            'timings': {}  # Add timings dictionary
        }
        
        now = datetime.today()
        logging.info(f"Collection started at: {now}")

        # Log device details before processing
        for d in devices:
            logging.info(f"Will process device: {d.router_name} ({d.router_ip})")

        # Use ThreadPoolExecutor to process devices in parallel
        max_workers = min(device_count, 5)  # Reduce concurrency to 5 threads
        logging.info(f"Using {max_workers} worker threads")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_single_device, d, shared_data): d 
                for d in devices  # Use devices list instead of device
            }
            
            # Wait for completion or timeout
            done, not_done = concurrent.futures.wait(
                futures,
                timeout=max_execution_time,
                return_when=concurrent.futures.ALL_COMPLETED
            )
            
            # Handle timeouts
            for future in not_done:
                device = futures[future]
                logging.error(f"Device {device.router_ip} timed out")
                future.cancel()
                handle_router_error(device.router_ip, device.router_name)
                
        elapsed = time.time() - collection_start
        logging.info(f"Collection cycle completed in {elapsed:.2f} seconds")

        # Verify collected data
        logging.info(f"Devices processed: {len(shared_data['resource_device'])}")
        logging.info(f"Traffic data collected: {len(shared_data['traffic_device'])}")
        logging.info(f"Interface data collected: {len(shared_data['interface_rb'])}")
        logging.info(f"Traffic aggregation collected: {len(shared_data['traffic_agg'])}")

        # Add timing summary after collection
        logging.info("\nCollection timing summary:")
        total_elapsed = time.time() - collection_start
        
        # Sort devices by collection time
        sorted_timings = sorted(shared_data['timings'].items(), key=lambda x: x[1], reverse=True)
        
        for ip, elapsed in sorted_timings:
            device = next((d for d in devices if d.router_ip == ip), None)  # Use devices list
            if device:
                logging.info(f"Router: {device.router_name} ({ip})")
                logging.info(f"├── Collection time: {elapsed:.2f} seconds")
                logging.info(f"└── Status: {'Success' if ip in shared_data['resource_device'] else 'Failed'}")
                
        logging.info(f"\nTotal collection cycle time: {total_elapsed:.2f} seconds")
        logging.info(f"Average device collection time: {sum(shared_data['timings'].values())/len(shared_data['timings']):.2f} seconds")

        # Use collected data from shared dictionary
        logging.info("In Progress, Starting to insert collected data to database")
        
        # Collection phase timing
        collect_end = time.time()
        collection_time = collect_end - collection_start
        
        # Database insertion timing
        logging.info("\nStarting database operations:")
        
        db_timings = {}
        
        start = time.time()
        into_db_resource(shared_data['resource_device'])
        db_timings['resources'] = time.time() - start
        
        start = time.time()
        into_db_user(shared_data['traffic_device'], "update_interval")
        db_timings['users'] = time.time() - start
        
        start = time.time()
        into_db_interface(shared_data['interface_rb'])
        db_timings['interfaces'] = time.time() - start
        
        start = time.time()
        into_db_traffic_agg(shared_data['traffic_agg'], shared_data['resource_device'])
        db_timings['traffic_agg'] = time.time() - start
        
        start = time.time()
        into_db_user_traffic_accumulate(shared_data['traffic_device'], "update_interval")
        db_timings['traffic_accumulate'] = time.time() - start

        # Print timing summary
        logging.info("\nComplete Timing Summary:")
        logging.info("------------------------")
        logging.info("Router Collection Phase:")
        
        # Sort devices by collection time
        sorted_timings = sorted(shared_data['timings'].items(), key=lambda x: x[1], reverse=True)
        
        for ip, elapsed in sorted_timings:
            device = next((d for d in devices if d.router_ip == ip), None)
            if device:
                logging.info(f"Router: {device.router_name} ({ip})")
                logging.info(f"├── Collection time: {elapsed:.2f} seconds")
                logging.info(f"└── Status: {'Success' if ip in shared_data['resource_device'] else 'Failed'}")
        
        logging.info("\nDatabase Operations Phase:")
        for operation, elapsed in db_timings.items():
            logging.info(f"├── {operation}: {elapsed:.2f} seconds")
        
        total_db_time = sum(db_timings.values())
        logging.info(f"└── Total DB Operations: {total_db_time:.2f} seconds")
        
        total_time = time.time() - collection_start
        logging.info(f"\nTotal Execution Time: {total_time:.2f} seconds")
        logging.info(f"├── Collection: {collection_time:.2f} seconds ({(collection_time/total_time)*100:.1f}%)")
        logging.info(f"└── Database Ops: {total_db_time:.2f} seconds ({(total_db_time/total_time)*100:.1f}%)")

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
        logging.error(f"Communication error in get_traffic_agg: {str(e)}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error in get_traffic_agg: {str(e)}")
        return None


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
        logging.error(f"Communication error in get_info: {str(e)}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error in get_info: {str(e)}")
        return None


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
        logging.error(f"Communication error in get_traffic: {str(e)}")
        return None, None
    except Exception as e:
        logging.error(f"Unexpected error in get_traffic: {str(e)}")
        return None, None

