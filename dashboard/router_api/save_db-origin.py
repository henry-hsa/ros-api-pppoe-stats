from monitor_app.models import Devices, DevicesInfo, UserInfo, ListInterface, TrafficAgg, UserTrafficAccumulation
from collections import Counter


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


def into_db_user(traffic_device, running_from):
    user_from_device = []

    if running_from == "update_interval":
        check_user = UserInfo.objects.values_list('user_pppoe', flat=True)
        check_user = list(check_user)

    else:
        ip = [key for key in traffic_device]
        ip = ip[0]
        check_user = UserInfo.objects.filter(
            router_ip=ip).values_list('user_pppoe', flat=True)
        check_user = list(check_user)

    for key in traffic_device:
        for item in traffic_device[key]:
            item_user = item.split(";")

            pppoe_user = item_user[0]
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
                user_update = UserInfo.objects.get(user_pppoe=pppoe_user)
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
            else:
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

            user_from_device.append(pppoe_user)

    for user_db in check_user:
        if user_db in user_from_device:
            continue
        elif user_db not in user_from_device:
            status = "Offline"
            update_status = UserInfo.objects.get(user_pppoe=user_db)
            update_status.status = status
            update_status.save()
            
# def into_db_user(traffic_device, running_from):
#     user_from_device = []

#     # Update logic untuk 'update_interval' dan bukan 'update_interval'
#     if running_from == "update_interval":
#         check_user = UserInfo.objects.values_list('user_pppoe', flat=True)
#         check_user = list(check_user)
#     else:
#         # Mengambil semua IP dari traffic_device
#         for key in traffic_device:
#             check_user = UserInfo.objects.filter(router_ip=key).values_list('user_pppoe', flat=True)
#             check_user = list(check_user)

#             for item in traffic_device[key]:
#                 item_user = item.split(";")
#                 pppoe_user = item_user[0]
#                 uptime = item_user[1]
#                 service = item_user[2]
#                 ipa_remote = item_user[3]
#                 mac_remote = item_user[4]
#                 rx_byte = item_user[5]
#                 tx_byte = item_user[6]
#                 interface_name = item_user[7]
#                 identity_router = item_user[8]
#                 status = "Online"

#                 if pppoe_user in check_user:
#                     user_update = UserInfo.objects.get(user_pppoe=pppoe_user)
#                     user_update.uptime = uptime
#                     user_update.service = service
#                     user_update.ip_address = ipa_remote
#                     user_update.mac_address = mac_remote
#                     user_update.rx_upload = rx_byte
#                     user_update.tx_download = tx_byte
#                     user_update.interface_name = interface_name
#                     user_update.identity_router = identity_router
#                     user_update.router_ip = key
#                     user_update.status = status
#                     user_update.save()
#                 else:
#                     user_add = UserInfo(
#                         user_pppoe=pppoe_user,
#                         uptime=uptime,
#                         service=service,
#                         ip_address=ipa_remote,
#                         mac_address=mac_remote,
#                         rx_upload=rx_byte,
#                         tx_download=tx_byte,
#                         interface_name=interface_name,
#                         identity_router=identity_router,
#                         router_ip=key,
#                         status=status
#                     )
#                     user_add.save()

#                 user_from_device.append(pppoe_user)

#             # Mark users as "Offline" for users not found in traffic_device
#             for user_db in check_user:
#                 if user_db not in user_from_device:
#                     status = "Offline"
#                     update_status = UserInfo.objects.get(user_pppoe=user_db)
#                     update_status.status = status
#                     update_status.save()



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
    user_from_device = []

    if running_from == "update_interval":
        check_user = UserTrafficAccumulation.objects.values_list(
            'user_pppoe', flat=True)
        check_user = list(check_user)

    else:
        ip = [key for key in traffic_device]
        ip = ip[0]
        check_user = UserTrafficAccumulation.objects.filter(
            router_ip=ip).values_list('user_pppoe', flat=True)
        check_user = list(check_user)

    for key in traffic_device:
        for item in traffic_device[key]:
            item_user = item.split(";")

            pppoe_user = item_user[0]
            rx_byte = item_user[5]
            tx_byte = item_user[6]
            identity_router = item_user[8]

            if pppoe_user in check_user:
                user_update = UserTrafficAccumulation.objects.get(
                    user_pppoe=pppoe_user)

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
                user_add = UserTrafficAccumulation(
                    user_pppoe=pppoe_user,
                    rx_upload=rx_byte,
                    tx_download=tx_byte,
                    old_rx_upload=rx_byte,
                    old_tx_download=tx_byte,
                    router_name=identity_router,
                    router_ip=key,
                )
                user_add.save()

# def into_db_user_traffic_accumulate(traffic_device, running_from):
#     user_from_device = []

#     # Jika running_from adalah 'update_interval', ambil semua pengguna yang ada di DB
#     if running_from == "update_interval":
#         check_user = UserTrafficAccumulation.objects.values_list('user_pppoe', flat=True)
#         check_user = list(check_user)
#     else:
#         # Mengambil IP dari traffic_device dan memproses per router
#         for key in traffic_device:
#             check_user = UserTrafficAccumulation.objects.filter(router_ip=key).values_list('user_pppoe', flat=True)
#             check_user = list(check_user)

#             for item in traffic_device[key]:
#                 item_user = item.split(";")

#                 pppoe_user = item_user[0]
#                 rx_byte = item_user[5]
#                 tx_byte = item_user[6]
#                 identity_router = item_user[8]

#                 if pppoe_user in check_user:
#                     user_update = UserTrafficAccumulation.objects.get(user_pppoe=pppoe_user)

#                     # Update user traffic accumulation based on the differences
#                     if int(rx_byte) < user_update.old_rx_upload:
#                         user_update.rx_upload += int(rx_byte)
#                         user_update.tx_download += int(tx_byte)
#                         user_update.old_rx_upload = rx_byte
#                         user_update.old_tx_download = tx_byte
#                     elif int(rx_byte) > user_update.old_rx_upload:
#                         fix_rx = int(rx_byte) - user_update.old_rx_upload
#                         fix_tx = int(tx_byte) - user_update.old_tx_download
#                         user_update.rx_upload += fix_rx
#                         user_update.tx_download += fix_tx

#                         user_update.old_rx_upload = rx_byte
#                         user_update.old_tx_download = tx_byte

#                     user_update.router_name = identity_router
#                     user_update.router_ip = key
#                     user_update.save()
#                 else:
#                     user_add = UserTrafficAccumulation(
#                         user_pppoe=pppoe_user,
#                         rx_upload=rx_byte,
#                         tx_download=tx_byte,
#                         old_rx_upload=rx_byte,
#                         old_tx_download=tx_byte,
#                         router_name=identity_router,
#                         router_ip=key,
#                     )
#                     user_add.save()

