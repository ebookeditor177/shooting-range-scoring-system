from django.db import models
from django.utils import timezone


class DeviceStatus(models.TextChoices):
    OFFLINE = 'offline', 'Offline'
    ONLINE = 'online', 'Online'
    REGISTERED = 'registered', 'Registered'
    ERROR = 'error', 'Error'


class Device(models.Model):
    """Represents an ESP32 device connected to a lane."""
    
    device_id = models.CharField(max_length=100, unique=True, db_index=True)
    serial_number = models.CharField(max_length=100, blank=True, default='')
    firmware_version = models.CharField(max_length=20, blank=True, default='')
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=DeviceStatus.choices,
        default=DeviceStatus.OFFLINE
    )
    is_online = models.BooleanField(default=False)
    
    # Configuration
    supported_sensors = models.JSONField(
        default=list,
        help_text="List of sensor positions, e.g. ['head', 'chest', 'stomach']"
    )
    
    # Connection info
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    
    # WebSocket channel
    channel_name = models.CharField(max_length=200, blank=True, default='')
    
    # Timestamps
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['device_id']
        verbose_name = 'Device'
        verbose_name_plural = 'Devices'
    
    def __str__(self):
        return f"Device {self.device_id} ({self.get_status_display()})"
    
    @property
    def is_alive(self):
        """Check if device has sent a heartbeat recently (within 30 seconds)."""
        if not self.last_heartbeat:
            return False
        delta = timezone.now() - self.last_heartbeat
        return delta.total_seconds() < 30
    
    def update_heartbeat(self):
        """Update the last heartbeat timestamp."""
        self.last_heartbeat = timezone.now()
        self.is_online = True
        self.status = DeviceStatus.ONLINE
        self.save(update_fields=['last_heartbeat', 'is_online', 'status', 'updated_at'])
    
    def mark_online(self, channel_name: str = None):
        """Mark device as online."""
        self.is_online = True
        self.status = DeviceStatus.ONLINE
        self.last_seen = timezone.now()
        if channel_name:
            self.channel_name = channel_name
        self.save(update_fields=['is_online', 'status', 'last_seen', 'channel_name', 'updated_at'])
    
    def mark_offline(self):
        """Mark device as offline."""
        self.is_online = False
        self.status = DeviceStatus.OFFLINE
        self.channel_name = ''
        self.save(update_fields=['is_online', 'status', 'channel_name', 'updated_at'])


class DeviceLog(models.Model):
    """Logs device events for debugging."""
    
    LEVEL_CHOICES = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
    ]
    
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='logs')
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='INFO')
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Device Log'
        verbose_name_plural = 'Device Logs'
        indexes = [
            models.Index(fields=['device', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.device.device_id} - {self.level}: {self.message[:50]}"
