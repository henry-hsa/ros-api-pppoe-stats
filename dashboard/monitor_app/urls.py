from django.urls import path
from django.views.generic.base import RedirectView
from . import views


urlpatterns = [
    path('monitor_app/', views.index, name='index'),
    path('', RedirectView.as_view(url='monitor_app/'), name='index'),
    path('devices/insert', views.insert, name='insert'),
    path('devices/edit', views.get_data_device_edit, name='edit-device'),
    path('devices/update', views.update, name='update-device'),
    path('devices/check-ip', views.check_ip_is_exist, name='check'),
    path('devices/', views.devices, name='devices'),
    path('devices_info/', views.devices_info, name='devices_info'),
    #Configure
    path('configure/', views.configure, name='configure'),
    path('verify_config/', views.verify_config, name='verify_config'),
    path('log/', views.log, name='log'),

    path('users_info/kick', views.user_kick, name='kick_user'),
    path('users_info/', views.users_info, name='users_info'),
    path('users_info/<str:status>', views.users_info, name='users_info'),
    path('info_devices_view/', views.DevicesInfoListView.as_view(), name="info-devices"),
    path('list_devices_view/', views.DevicesListView.as_view(), name="list-devices"),
    path('list_users_view/', views.UserInfoListView.as_view(), name="list-users-pppoe"),
    path('list_users_view/', views.UserInfoListView.as_view(), name="list-users-pppoe"),
    path('create_graph_interface', views.interface_graph, name='graph-interface'),
    path('check-interface', views.get_list_interface, name='check-graph-interface'),
    path('monitor_app/get-traffic-agg/', views.get_traffic_agg, name='traffic-agg'),
    path('user_accumulate/', views.user_traffic_accumulate, name='user-acumulate'),
    path('list_users_accumulate/', views.UserTrafficAccumulationListView.as_view(), name="list-users-accumulate"),
    path('userlogin/', views.userlogin, name='userlogin'),
    path('userlogin/insertuser', views.insertuser, name='insertuser'),
    path('list_user_login_view/', views.UserLoginListView.as_view(), name="list-user-login"),
]