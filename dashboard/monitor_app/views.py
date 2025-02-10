from collections import Counter
from django.core import serializers, exceptions
from django.shortcuts import render, HttpResponse, redirect
from django.http import HttpResponseBadRequest, JsonResponse
from .models import Devices, DevicesInfo, ListInterface, TrafficAgg, UserInfo, UserTrafficAccumulation, UserLogin
from .models import Device, Log
from django.shortcuts import render
from django.shortcuts import get_object_or_404, redirect
from ajax_datatable.views import AjaxDatatableView
from django.utils.html import escape
from router_api.collect import convert_bytes, convert_bytes_only
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from django.utils import timezone

import json
import paramiko


class DevicesListView(AjaxDatatableView):
    model = Devices
    length_menu = [[10, 20, 50, 100, -1], [10, 20, 50, 100, 'all']]
    search_values_separator = '+'

    def customize_row(self, row, obj):
        cek = obj.pk
        row['edit'] = f"""
        <button type="button" onclick="getDataEdit({cek})" title="Edit" class="btn btn-outline-warning btn-xs" data-toggle="modal" data-target="#editdevices">
            <i class="fas fa-fw fa-edit"></i>
        </button>
        """
        return
    # def customize_row1(self, row, obj):
    #     cek = obj.pk
    #     row['remote'] = f"""
    #     <button type="button" onclick="http://{{router_ip}}/" title="Remote" class="btn btn-outline-primary btn-xs" data-toggle="modal" data-target="#editdevices">
    #         <i class="fas fa-fw fa-edit"></i>
    #     </button>
    #     """
    #     return

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'router_name', 'visible': True, },
        {'name': 'router_ip', 'visible': True, },
        {'name': 'location', 'visible': True, },
        {'name': 'edit', 'title': 'Edit', 'placeholder': True,
            'searchable': False, 'orderable': False, },
        # {'name': 'remote', 'title': 'Remote', 'placeholder': True,
        #     'searchable': False, 'orderable': False, }

    ]


class DevicesInfoListView(AjaxDatatableView):
    model = DevicesInfo
    length_menu = [[10, 20, 50, 100, -1], [10, 20, 50, 100, 'all']]
    search_values_separator = '+'

    def render_row_details(self, pk, request=None):
        return super().render_row_details(pk, request)
    
    # def customize_row(self, row, obj):
    #     cek = obj.router_ip
    #     row['remote'] = f"""
    #     <button type="button" onclick="http://{{cek}}/" title="Edit" class="btn btn-outline-warning btn-xs" data-toggle="modal" data-target="#editdevices">
    #         <i class="fas fa-fw fa-edit"></i>
    #     </button>
    #     """
    #     return

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'router_name', 'visible': True, },
        {'name': 'router_ip', 'visible': True},
        {'name': 'router_type', 'visible': True},
        {'name': 'os_version', 'visible': True},
        {'name': 'serial_number', 'visible': True},
        {'name': 'uptime', 'visible': True},
        # {'name': 'edit', 'title': 'Edit', 'placeholder': True,
        #     'searchable': False, 'orderable': False, },
        {'name': 'pk', 'visible': False, 'searchable': False, },
    ]


class UserInfoListView(AjaxDatatableView):
    model = UserInfo
    length_menu = [[10, 20, 50, 100, -1], [10, 20, 50, 100, 'all']]
    search_values_separator = '+'

    def get_initial_queryset(self, request=None):
        queryset = super().get_initial_queryset(request)
        
        # Get both POST and GET parameters to handle both AJAX and direct URL access
        select_status = self.request.POST.get('select_status') or self.request.GET.get('status')
        select_device = self.request.POST.get('select_device') or self.request.GET.get('device')
        
        if select_status:
            queryset = queryset.filter(status=select_status)
        if select_device:
            queryset = queryset.filter(identity_router=select_device)
            
        return queryset

    def render_column(self, row, column):
        if column == "rx_upload":
            new_format = convert_bytes(row.rx_upload)
            return escape('{0}'.format(new_format))
        if column == "tx_download":
            new_format = convert_bytes(row.tx_download)
            return escape('{0}'.format(new_format))
        else:
            return super().render_column(row, column)

    def render_row_details(self, pk, request=None):
        detail_user = self.model.objects.filter(pk=pk).values()[0]
        user_detail = detail_user.pop('id')
        details = {}

        for key, value in detail_user.items():
            if key == 'rx_upload' or key == 'tx_download':
                value = convert_bytes(value)

            details[key] = value

        return render_to_string('pages/row_details/user_info_kick_button.html', {
            'user': detail_user['user_pppoe'],
            'detail': details.items(),
            'status': detail_user["status"]
        }),

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'identity_router', 'visible': True},
        {'name': 'user_pppoe', 'visible': True},
        {'name': 'service', 'visible': True},
        {'name': 'ip_address', 'visible': True},
        {'name': 'mac_address', 'visible': True},
        {'name': 'rx_upload', 'title': 'Upload', 'visible': True},
        {'name': 'tx_download', 'title': 'Download', 'visible': True},
        {'name': 'status', 'visible': True},
        {'name': 'pk', 'visible': False, 'searchable': False, },
    ]


class UserTrafficAccumulationListView(AjaxDatatableView):
    model = UserTrafficAccumulation
    length_menu = [[10, 20, 50, 100, -1], [10, 20, 50, 100, 'all']]
    search_values_separator = '+'

    def render_column(self, row, column):
        if column == "rx_upload":
            new_format = convert_bytes(row.rx_upload)
            return escape('{0}'.format(new_format))
        if column == "tx_download":
            new_format = convert_bytes(row.tx_download)
            return escape('{0}'.format(new_format))
        else:
            return super().render_column(row, column)

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'router_name', 'visible': True, },
        {'name': 'user_pppoe', 'visible': True},
        {'name': 'rx_upload', 'title': 'Upload',
            'visible': True, 'searchable': False},
        {'name': 'tx_download', 'title': 'Download',
            'visible': True, 'searchable': False}
    ]

class UserLoginListView(AjaxDatatableView):
    model = UserLogin
    length_menu = [[10, 20, 50, 100, -1], [10, 20, 50, 100, 'all']]
    # search_values_separator = '+'

    def customize_row(self, row, obj):
        cek = obj.pk
        row['edit'] = f"""
        <button type="button" onclick="getDataEdit({cek})" title="Edit" class="btn btn-outline-warning btn-xs" data-toggle="modal" data-target="#editdevices">
            <i class="fas fa-fw fa-edit"></i>
        </button>
        """
        return

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'username', 'visible': True, },
        {'name': 'first_name', 'visible': True, },
        {'name': 'email', 'visible': True, },
        {'name': 'edit', 'title': 'Edit', 'placeholder': True,
            'searchable': False, 'orderable': False, }

    ]


@login_required
def user_traffic_accumulate(request):
    return render(request, 'pages/user_traffic_accumulate.html')


@login_required
def index(request):
    # Get devices with their info
    all_devices = Devices.objects.all().select_related()
    all_users = UserInfo.objects.all()
    users_online = UserInfo.objects.filter(status="Online")
    users_offline = UserInfo.objects.filter(status="Offline")
    
    # Get devices info for proper naming
    devices_info = DevicesInfo.objects.all()
    device_names = {d.router_ip: d.router_name for d in devices_info}
    
    # Calculate users per device using device info names
    users_per_device = {}
    for device in all_devices:
        device_name = device_names.get(device.router_ip, device.router_name)
        device_users = UserInfo.objects.filter(identity_router=device_name)
        users_per_device[device_name] = {
            'total': device_users.count(),
            'online': device_users.filter(status="Online").count(),
            'offline': device_users.filter(status="Offline").count(),
            'router_ip': device.router_ip
        }

    try:
        latest_updated = TrafficAgg.objects.filter(
            update_time__isnull=False).latest('update_time')
        result = latest_updated.update_time
    except TrafficAgg.DoesNotExist:
        result = None

    # Add online users data for graph
    online_users_data = {
        'labels': [],
        'data': [],
        'device_names': []  # Add this to store device names for filtering
    }
    
    for device in all_devices:
        device_name = device_names.get(device.router_ip, device.router_name)
        online_count = UserInfo.objects.filter(
            identity_router=device_name,
            status="Online"
        ).count()
        online_users_data['labels'].append(device_name)
        online_users_data['data'].append(online_count)
        online_users_data['device_names'].append(device_name)  # Store device name

    context = {
        'devices_count': all_devices.count(),
        'users_count': all_users.count(),
        'users_online': users_online.count(),
        'users_offline': users_offline.count(),
        'chart_data': TrafficAgg.objects.all(),  # Keep original chart_data query
        'routers': devices_info.values('router_name', 'router_ip').distinct(),
        'latest_update': result,
        'online_users_data': online_users_data,
        'users_per_device': users_per_device,
    }
    return render(request, 'pages/dashboard.html', context)


@login_required
def devices(request):
    return render(request, 'pages/devices.html')

@login_required
def userlogin(request):
    return render(request, 'pages/userlogin.html')


@login_required
def users_info(request, status=None):
    context = {
        'status': '' if not status else status
    }
    return render(request, 'pages/users_info.html', context)


@login_required
def devices_info(request):
    return render(request, 'pages/devices_info.html')


@login_required
def interface_graph(request):
    check_int = ListInterface.objects.values('router_name', 'router_ip')
    list_router = list({v['router_ip']: v for v in check_int}.values())
    context = {
        'list_routers': list_router
    }
    return render(request, 'pages/create-graphs.html', context)


@login_required
def insert(request):
    devices = Devices(
        router_name=request.POST['router_name'],
        router_ip=request.POST['router_ip'],
        location=request.POST['location'],
        username=request.POST['username'],
        password=request.POST['password'],
    )
    devices.save()
    return redirect('/monitor_app')

@login_required
def insertuser(request):
    userlogin = UserLogin(
        username=request.POST['username'],
        first_name=request.POST['first_name'],
        last_name=request.POST['last_name'],
        email=request.POST['email'],
        password=request.POST['password'],
    )
    userlogin.save()
    return redirect('/monitor_app')


@login_required
def update(request):

    if request.method == 'POST':

        device_update = Devices.objects.get(id=request.POST['idnya'])

        if device_update.router_ip != request.POST['router_ip']:
            check_if_exist = DevicesInfo.objects.filter(
                router_ip=device_update.router_ip).exists()
            if check_if_exist:

                device_info_update = DevicesInfo.objects.get(
                    router_ip=device_update.router_ip)
                device_info_update.router_ip = request.POST['router_ip']
                device_info_update.save()

            bulk_updates = []
            traffic_aggs = TrafficAgg.objects.filter(
                router_ip=device_update.router_ip)
            if traffic_aggs.exists():
                for traffic_agg in traffic_aggs:
                    traffic_agg.router_ip = request.POST['router_ip']
                    bulk_updates.append(traffic_agg)

                TrafficAgg.objects.bulk_update(
                    bulk_updates, ['router_ip'], batch_size=1000)

        device_update.router_name = request.POST['router_name']
        device_update.router_ip = request.POST['router_ip']
        device_update.location = request.POST['location']
        device_update.username = request.POST['username']
        device_update.password = request.POST['password']
        device_update.save()

        return JsonResponse({'status': "Data Successfully Updated"})

    return JsonResponse({'status': 'Invalid request'}, status=400)


@login_required
@csrf_exempt
def user_kick(request):
    from router_api.action import kick
    pppoe_user = request.POST['user_nya']
    check_user = UserInfo.objects.filter(user_pppoe=pppoe_user).first()

    if check_user:
        print(check_user.router_ip)
        result, status = kick(check_user.router_ip, check_user.user_pppoe)

        if result == f"success_{check_user.user_pppoe}":
            print(result, status)
            return JsonResponse({'msg': check_user.user_pppoe}, status=status)
        else:
            print(result)
            return JsonResponse({'status': str(result)}, status=status)

    else:
        return JsonResponse({'status': 'Invalid request'}, status=status)


@login_required
def check_ip_is_exist(request):

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if is_ajax:
        if request.method == 'POST':
            data = json.load(request)
            ipnya = data.get('payload')
            data_ip = Devices.objects.filter(router_ip=ipnya).first()
            result = data_ip.router_ip if data_ip else ""
            return JsonResponse({'my_data': result})
        return JsonResponse({'status': 'Invalid request'}, status=400)
    else:
        return HttpResponseBadRequest('Invalid request')


@login_required
def get_data_device_edit(request):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if is_ajax:
        if request.method == 'POST':
            data = json.load(request)
            pk = data.get('payload')
            data_ip = Devices.objects.filter(id=pk).first()
            print(data_ip.router_ip)
            data_sent = serializers.serialize('json', [data_ip], fields=[
                                              'router_name', 'router_ip', 'location', 'username', 'id'])

            return HttpResponse(data_sent, content_type='application/json')
        return JsonResponse({'status': 'Invalid request'}, status=400)
    else:
        return HttpResponseBadRequest('Invalid request')


@login_required
def get_list_interface(request):

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if is_ajax:
        if request.method == 'POST':
            data = json.load(request)
            ipnya = data.get('payload')
            interface = ListInterface.objects.filter(
                router_ip=ipnya).values_list("interface_name", flat=True)
            interface_list = list(interface)

            return JsonResponse({'data': interface_list})
        return JsonResponse({'status': 'Invalid request'}, status=400)
    else:
        return HttpResponseBadRequest('Invalid request')


@login_required
def get_traffic_agg(request):
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return HttpResponseBadRequest('Invalid request')

    router_name_nya = request.GET.get('data_nya')
    interval_nya = request.GET.get('interval', 'time_30')
    
    if not router_name_nya:
        return JsonResponse({'status': 'No router name provided'}, status=400)

    try:
        # Calculate time range
        now = timezone.now()
        if interval_nya == "time_5":
            default = now - timedelta(minutes=5)
        elif interval_nya == "time_30":
            default = now - timedelta(minutes=30)
        elif interval_nya == "time_60":
            default = now - timedelta(minutes=60)
        elif interval_nya == "1_day":
            default = now - timedelta(days=1)
        elif interval_nya == "3_day":
            default = now - timedelta(days=3)
        elif interval_nya == "7_day":
            default = now - timedelta(days=7)
        else:
            default = now - timedelta(minutes=30)

        # Get traffic data
        traffic_data = TrafficAgg.objects.filter(
            router_ip=router_name_nya,
            update_time__gte=default
        ).order_by('update_time')

        # Process data
        result = {
            'label_cpu': [],
            'dataset_cpu': [],
            'upload': [],
            'download': [],
            'router_name': router_name_nya,
            'satuan_upload': '',
            'satuan_download': ''
        }

        for data in traffic_data:
            result['label_cpu'].append(data.update_time.strftime("%Y-%m-%d %H:%M:%S"))
            result['dataset_cpu'].append(data.cpu_load)
            
            if data.upload and data.download:
                upload, satuan_upload = convert_bytes_only(int(data.upload))
                download, satuan_download = convert_bytes_only(int(data.download))
                result['upload'].append(upload)
                result['download'].append(download)
                result['satuan_upload'] = satuan_upload
                result['satuan_download'] = satuan_download
            else:
                result['upload'].append(0)
                result['download'].append(0)

        result['status'] = 'success'
        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({'status': str(e)}, status=500)

#Configuration
@login_required
def configure(request):
    if request.method == "POST":
        selected_device_id = request.POST.getlist('device')
        mikrotik_command = request.POST['mikrotik_command'].splitlines()
        cisco_command = request.POST['cisco_command'].splitlines()
        for x in selected_device_id:
            try:
                dev = get_object_or_404(Device, pk=x)
                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh_client.connect(hostname=dev.ip_address, username=dev.username, password=dev.password)

                if dev.vendor.lower() == 'cisco':
                    conn = ssh_client.invoke_shell()
                    conn.send("conf t\n")
                    for cmd in cisco_command:
                        conn.send(cmd + "\n")
                        time.sleep(1)
                else:
                    for cmd in mikrotik_command:
                        ssh_client.exec_command(cmd)

                log = Log(target=dev.ip_address, action="Configure", status="Success", time=datetime.now(), messages="Nice Run")
                log.save()
            except Exception as e:
                log = Log(target=dev.ip_address, action="Configure", status="Error", time=datetime.now(), messages=e)
                log.save()
        
        return redirect('dashboard.html')
    else:
        devices = Device.objects.all()
        context = {
            'device': devices
        }
        return render(request, 'pages/configure.html', context)

@login_required
def verify_config(request):
    if request.method == "POST":
        result = []
        selected_device_id = request.POST.getlist('device')
        mikrotik_command = request.POST['mikrotik_command'].splitlines()
        cisco_command = request.POST['cisco_command'].splitlines()
        for x in selected_device_id:
            try:
                dev = get_object_or_404(Device, pk=x)
                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh_client.connect(hostname=dev.ip_address, username=dev.username, password=dev.password)

                if dev.vendor.lower() == 'mikrotik':
                    for cmd in mikrotik_command:
                        stdin, stdout, stderr = ssh_client.exec_command(cmd)
                        time.sleep(1)
                        result.append("Result on {0}".format(dev.ip_address))
                        result.append(stdout.read().decode())
                else:
                    conn = ssh_client.invoke_shell()
                    conn.send('terminal length 0\n')
                    for cmd in cisco_command:
                        result.append("Result on {0}".format(dev.ip_address)) 
                        conn.send(cmd + "\n")           
                        time.sleep(1)
                        output = conn.recv(65535)
                        result.append(output.decode())
                log = Log(target=dev.ip_address, action="Verify Configuration", status="Success", time=datetime.now(), messages="Nice Run")
                log.save()
            except Exception as e:
                log = Log(target=dev.ip_address, action="Verify Configuration", status="Error", time=datetime.now(), messages=e)
                log.save()

        result = '\n'.join(result)
        return render(request, 'pages/verify_config.html', {'result' : result})

    else:
        devices = Device.objects.all()
        context = {
            'devices': devices
        }
        return render(request, 'pages/configure.html', context)

@login_required
def log(request):
    return render(request, 'pages/log.html')
