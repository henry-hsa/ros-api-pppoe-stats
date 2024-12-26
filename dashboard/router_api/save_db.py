import logging
from collections import Counter
from django.db.models import Max, Count, Q
from django.db import transaction, connections
from django.db.utils import OperationalError
from time import sleep
from monitor_app.models import (
    Devices, 
    DevicesInfo, 
    UserInfo, 
    ListInterface, 
    TrafficAgg, 
    UserTrafficAccumulation
)

def clean_duplicate_users():
    """Clean up duplicate PPPoE users by keeping only the most recent entry"""
    try:
        with transaction.atomic():
            # Get all PPPoE users with duplicates
            duplicates = UserInfo.objects.values('user_pppoe', 'identity_router').annotate(
                count=Count('id')).filter(count__gt=1)
            
            for dup in duplicates:
                user_pppoe = dup['user_pppoe']
                identity_router = dup['identity_router']
                # Get all entries for this user on this router
                entries = UserInfo.objects.filter(
                    user_pppoe=user_pppoe,
                    identity_router=identity_router
                ).order_by('-id')
                
                # Keep the most recent entry (first one) and delete others
                if entries.exists():
                    recent_entry = entries.first()
                    entries.exclude(id=recent_entry.id).delete()
                    logging.info(f"Cleaned up duplicates for user: {user_pppoe} on router: {identity_router}")
    except Exception as e:
        logging.error(f"Error cleaning duplicates: {e}")

def into_db_resource(resource_devices):
    check_resource = DevicesInfo.objects.values_list('router_ip', flat=True)
    check_resource = list(check_resource)

    for key in resource_devices:
        string_resource = resource_devices[key][0]
        item_resource = string_resource.split(";")

        if key in check_resource:
            update_resource = DevicesInfo.objects.get(router_ip=key)
            update_resource.router_type = item_resource[1]
            update_resource.os_version = item_resource[5]
            update_resource.memory_usage = item_resource[3]
            update_resource.cpu_usage = item_resource[4]
            update_resource.uptime = item_resource[2]
            update_resource.serial_number = item_resource[6]

            update_resource.save()
        else:
            resource_info_save = DevicesInfo(
                router_name=item_resource[0],
                router_ip=key,
                router_type=item_resource[1],
                os_version=item_resource[5],
                memory_usage=item_resource[3],
                cpu_usage=item_resource[4],
                uptime=item_resource[2],
                serial_number=item_resource[6],
            )
            resource_info_save.save()

def retry_on_deadlock(func, max_attempts=3, wait_time=1):
    """Retry function on deadlock with exponential backoff"""
    for attempt in range(max_attempts):
        try:
            return func()
        except OperationalError as e:
            if attempt == max_attempts - 1 or 'deadlock' not in str(e).lower():
                raise
            sleep(wait_time * (2 ** attempt))

def into_db_user(traffic_device, running_from):
    try:
        # Clean up any existing duplicates first
        clean_duplicate_users()
        
        # Initialize variables outside transaction
        user_from_device = set()
        processed_users = set()
        check_user = set()

        # Get current users before transaction
        if running_from == "update_interval":
            current_users = UserInfo.objects.values_list('user_pppoe', flat=True)
            check_user = set(current_users)
        else:
            ip = [key for key in traffic_device][0]
            current_users = UserInfo.objects.filter(
                router_ip=ip).values_list('user_pppoe', flat=True)
            check_user = set(current_users)

        # Process users in batches to avoid long transactions
        batch_size = 25
        updates = []
        new_users = []

        for key in traffic_device:
            for item in traffic_device[key]:
                try:
                    item_user = item.split(";")
                    pppoe_user = item_user[0]
                    
                    if (pppoe_user, key) in processed_users:
                        continue
                        
                    processed_users.add((pppoe_user, key))
                    user_from_device.add(pppoe_user)

                    uptime = item_user[1]
                    service = item_user[2]
                    ipa_remote = item_user[3]
                    mac_remote = item_user[4]
                    rx_byte = item_user[5]
                    tx_byte = item_user[6]
                    interface_name = item_user[7]
                    identity_router = item_user[8]
                    status = "Online"

                    if pppoe_user in check_user:
                        try:
                            with transaction.atomic():
                                user_update = UserInfo.objects.filter(
                                    user_pppoe=pppoe_user,
                                    identity_router=identity_router
                                ).order_by('-id').first()
                                
                                if user_update:
                                    user_update.uptime = uptime
                                    user_update.service = service
                                    user_update.ip_address = ipa_remote
                                    user_update.mac_address = mac_remote
                                    user_update.rx_upload = rx_byte
                                    user_update.tx_download = tx_byte
                                    user_update.interface_name = interface_name
                                    user_update.identity_router = identity_router
                                    user_update.router_ip = key
                                    user_update.status = status
                                    user_update.save()
                        except Exception as e:
                            logging.error(f"Error updating user {pppoe_user}: {e}")
                            continue
                    else:
                        try:
                            with transaction.atomic():
                                user_add = UserInfo(
                                    user_pppoe=pppoe_user,
                                    uptime=uptime,
                                    service=service,
                                    ip_address=ipa_remote,
                                    mac_address=mac_remote,
                                    rx_upload=rx_byte,
                                    tx_download=tx_byte,
                                    interface_name=interface_name,
                                    identity_router=identity_router,
                                    router_ip=key,
                                    status=status
                                )
                                user_add.save()
                        except Exception as e:
                            logging.error(f"Error adding new user {pppoe_user}: {e}")
                            continue

                except (IndexError, ValueError) as e:
                    logging.error(f"Error processing traffic data item: {e}")
                    continue

        # Update offline users in batches
        if running_from == "update_interval":
            try:
                with transaction.atomic():
                    UserInfo.objects.filter(
                        ~Q(user_pppoe__in=user_from_device)
                    ).update(status="Offline")
            except Exception as e:
                logging.error(f"Error updating offline users: {e}")

    except Exception as e:
        logging.error(f"Error in into_db_user: {e}")
        raise


def into_db_interface(interface_rb):
    check_int = ListInterface.objects.values_list('interface_name', flat=True)
    check_int = list(check_int)

    check_int_ip = ListInterface.objects.values_list('router_ip', flat=True)
    check_int_ip = Counter(list(check_int_ip))

    check_mac = ListInterface.objects.values_list('mac_address', flat=True)
    check_mac = Counter(list(check_mac))

    for key in interface_rb:
        if not interface_rb[key]:
            continue

        for item in interface_rb[key]:
            int_name = item.split(";")
            interface_name = int_name[0]
            mac_address = int_name[3]

            if interface_name in check_int and key in check_int_ip and mac_address in check_mac:
                continue
            else:
                interface_info_save = ListInterface(
                    router_ip=key,
                    router_name=int_name[1],
                    type_interface=int_name[2],
                    interface_name=interface_name,
                    mac_address=mac_address,
                )

                interface_info_save.save()


def into_db_traffic_agg(traffic_agg, resource_device):

    for key in traffic_agg:
        resource = resource_device[key][0]
        item = traffic_agg[key]
        item_string = item.split(";")
        item_resource = resource.split(";")
        cpu = item_resource[4].split('%')
        cpu_load = cpu[0]

        item_save = TrafficAgg(
            router_ip=key,
            router_name=item_resource[0],
            upload=item_string[0],
            download=item_string[1],
            cpu_load=cpu_load
        )
        item_save.save()


def into_db_user_traffic_accumulate(traffic_device, running_from):
    try:
        cursor = connections['default'].cursor()
        # Increase timeout and set isolation level
        cursor.execute('SET SESSION innodb_lock_wait_timeout=120')
        cursor.execute('SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED')
        
        user_from_device = set()
        # Process in smaller chunks
        chunk_size = 10
        
        for key in traffic_device:
            chunks = [traffic_device[key][i:i + chunk_size] 
                     for i in range(0, len(traffic_device[key]), chunk_size)]
            
            for chunk in chunks:
                with transaction.atomic():
                    if running_from == "update_interval":
                        # Remove skip_locked and use normal select_for_update
                        check_user = list(UserTrafficAccumulation.objects.select_for_update().values_list(
                            'user_pppoe', flat=True))
                    else:
                        check_user = list(UserTrafficAccumulation.objects.select_for_update().filter(
                            router_ip=key).values_list('user_pppoe', flat=True))

                    for item in chunk:
                        try:
                            item_user = item.split(";")
                            pppoe_user = item_user[0]
                            
                            if pppoe_user in user_from_device:
                                continue
                                
                            rx_byte = item_user[5]
                            tx_byte = item_user[6]
                            identity_router = item_user[8]

                            def update_or_create():
                                if pppoe_user in check_user:
                                    # Remove skip_locked here too
                                    user_update = UserTrafficAccumulation.objects.select_for_update().filter(
                                        user_pppoe=pppoe_user
                                    ).first()

                                    if user_update:
                                        if int(rx_byte) < user_update.old_rx_upload:
                                            user_update.rx_upload += int(rx_byte)
                                            user_update.tx_download += int(tx_byte)
                                            user_update.old_rx_upload = rx_byte
                                            user_update.old_tx_download = tx_byte
                                        elif int(rx_byte) > user_update.old_rx_upload:
                                            fix_rx = int(rx_byte) - user_update.old_rx_upload
                                            fix_tx = int(tx_byte) - user_update.old_tx_download
                                            user_update.rx_upload += fix_rx
                                            user_update.tx_download += fix_tx
                                            user_update.old_rx_upload = rx_byte
                                            user_update.old_tx_download = tx_byte

                                        user_update.router_name = identity_router
                                        user_update.router_ip = key
                                        user_update.save()
                                else:
                                    UserTrafficAccumulation.objects.create(
                                        user_pppoe=pppoe_user,
                                        rx_upload=rx_byte,
                                        tx_download=tx_byte,
                                        old_rx_upload=rx_byte,
                                        old_tx_download=tx_byte,
                                        router_name=identity_router,
                                        router_ip=key
                                    )

                            retry_on_deadlock(update_or_create)
                            user_from_device.add(pppoe_user)

                        except Exception as e:
                            logging.error(f"Error processing traffic accumulation for user {pppoe_user}: {e}")
                            continue

    except Exception as e:
        logging.error(f"Error in traffic accumulation: {e}")
        raise
