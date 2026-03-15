"""Device API views."""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from shooting_range.devices.models import Device, DeviceLog
from shooting_range.devices.api.serializers import DeviceSerializer, DeviceLogSerializer


class DeviceViewSet(viewsets.ModelViewSet):
    """API endpoint for devices."""
    
    queryset = Device.objects.all()
    lookup_field = 'device_id'
    serializer_class = DeviceSerializer
    
    def get_queryset(self):
        queryset = Device.objects.all()
        
        # Filter by status
        is_online = self.request.query_params.get('is_online')
        if is_online is not None:
            queryset = queryset.filter(is_online=is_online.lower() == 'true')
        
        # Filter by lane
        lane = self.request.query_params.get('lane')
        if lane:
            queryset = queryset.filter(lane__lane_number=lane)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def register(self, request, device_id=None):
        """Register a device."""
        device = self.get_object()
        
        device.status = 'registered'
        device.save()
        
        return Response(DeviceSerializer(device).data)
    
    @action(detail=True, methods=['post'])
    def ping(self, request, device_id=None):
        """Ping a device."""
        device = self.get_object()
        
        device.update_heartbeat()
        
        return Response({
            'device_id': device.device_id,
            'is_online': device.is_online,
            'last_heartbeat': device.last_heartbeat
        })
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get status of all devices."""
        devices = Device.objects.all()
        data = []
        
        for device in devices:
            data.append({
                'device_id': device.device_id,
                'is_online': device.is_online,
                'status': device.status,
                'last_seen': device.last_seen.isoformat() if device.last_seen else None,
                'last_heartbeat': device.last_heartbeat.isoformat() if device.last_heartbeat else None,
                'lane_number': device.lane.lane_number if device.lane else None
            })
        
        return Response(data)


class DeviceLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for device logs (read-only)."""
    
    queryset = DeviceLog.objects.all()
    serializer_class = DeviceLogSerializer
    
    def get_queryset(self):
        queryset = DeviceLog.objects.all()
        
        # Filter by device
        device_id = self.request.query_params.get('device_id')
        if device_id:
            queryset = queryset.filter(device__device_id=device_id)
        
        # Filter by level
        level = self.request.query_params.get('level')
        if level:
            queryset = queryset.filter(level=level.upper())
        
        return queryset
