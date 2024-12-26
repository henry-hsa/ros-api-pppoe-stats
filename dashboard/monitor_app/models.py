from django.db import models
from django.utils import timezone

# Create your models here.
class Devices(models.Model):
    router_name = models.CharField(max_length=255)
    router_ip = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)

    # def _str_(self):
    #     return self.router_name

class DevicesInfo(models.Model):
    router_name = models.CharField(max_length=255)
    router_ip = models.CharField(max_length=255)
    router_type = models.CharField(max_length=255)
    os_version = models.CharField(max_length=255)
    memory_usage = models.CharField(max_length=255)
    cpu_usage = models.CharField(max_length=255)
    uptime = models.CharField(max_length=255)
    serial_number = models.CharField(max_length=255, null=True)

    # def _str_(self):
    #     return self.router_name

class UserInfo(models.Model):
    interface_name = models.CharField(max_length=255)
    user_pppoe = models.CharField(max_length=255)
    uptime = models.CharField(max_length=255)
    service = models.CharField(max_length=255)
    ip_address = models.CharField(max_length=255)
    mac_address = models.CharField(max_length=255)
    rx_upload = models.BigIntegerField()
    tx_download = models.BigIntegerField()
    router_ip = models.CharField(max_length=255, null=True)
    identity_router = models.CharField(max_length=255, null=True)
    status = models.CharField(max_length=255, null=True)

    # def _str_(self):
    #     return self.user_pppoe

class ListInterface(models.Model):
    router_ip = models.CharField(max_length=255)
    router_name = models.CharField(max_length=255)
    interface_name = models.CharField(max_length=255)
    type_interface = models.CharField(max_length=255)
    mac_address = models.CharField(max_length=255, null=True)


class TrafficAgg(models.Model):
    router_ip = models.CharField(max_length=255)
    router_name = models.CharField(max_length=255)
    download = models.CharField(max_length=255)
    upload = models.CharField(max_length=255)
    update_time = models.DateTimeField(default=timezone.now)
    cpu_load = models.CharField(max_length=255, null=True)

    def json(self):
        return {
            'upload':    self.upload,
            'download': self.download,
            'update_time':   str(self.update_time),
            'cpu_load' : self.cpu_load
        }

class UserTrafficAccumulation(models.Model):
    router_ip = models.CharField(max_length=255)
    router_name = models.CharField(max_length=255)
    user_pppoe = models.CharField(max_length=255)
    old_rx_upload = models.BigIntegerField()
    old_tx_download = models.BigIntegerField()
    rx_upload = models.BigIntegerField()
    tx_download = models.BigIntegerField()

class UserLogin(models.Model):
    username = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    password = models.CharField(max_length=255)


# #Configuration
class Device(models.Model):
    ip_address = models.CharField(max_length=255)
    hostname = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    ssh_port = models.IntegerField(default=22)

    VENDOR_CHOICES = {  
        ('mikrotik','Mikrotik'),    
        ('cisco', 'Cisco')
    }

    vendor = models.CharField(max_length=255, choices=VENDOR_CHOICES)

    def __str__(self):
        return "{0} - {1}".format(self.hostname, self.ip_address)


class Log(models.Model):
    target = models.CharField(max_length=255)
    action = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    time = models.DateTimeField(null=True)
    messages = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return "{0} - {1} - {2}".format(self.target, self.action, self.status)