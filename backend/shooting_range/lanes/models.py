from django.db import models
from django.conf import settings


class Lane(models.Model):
    """Represents a shooting lane with its associated hardware and state."""
    
    lane_number = models.PositiveIntegerField(unique=True, db_index=True)
    name = models.CharField(max_length=100, blank=True, default='')
    is_active = models.BooleanField(default=True)
    is_enabled = models.BooleanField(default=True)
    
    # Target configuration
    enabled_sensors = models.JSONField(
        default=list,
        help_text="List of enabled sensor positions, e.g. ['head', 'chest', 'stomach']"
    )
    
    # Hardware association
    device = models.OneToOneField(
        'devices.Device',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lane'
    )
    
    # Display settings
    primary_color = models.CharField(max_length=7, default='#00FF00', help_text="Primary brand color")
    secondary_color = models.CharField(max_length=7, default='#000000', help_text="Secondary brand color")
    logo_url = models.URLField(blank=True, default='')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['lane_number']
        verbose_name = 'Lane'
        verbose_name_plural = 'Lanes'
    
    def __str__(self):
        return f"Lane {self.lane_number}: {self.name or 'Unnamed'}"
    
    @property
    def is_connected(self):
        """Check if the device is connected and responding."""
        if self.device:
            return self.device.is_online
        return False


class LaneScore(models.Model):
    """Tracks the current score for a lane during a game."""
    
    lane = models.ForeignKey(Lane, on_delete=models.CASCADE, related_name='scores')
    game = models.ForeignKey('games.Game', on_delete=models.CASCADE, related_name='lane_scores')
    score = models.PositiveIntegerField(default=0)
    hit_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    last_hit_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['lane', 'game']
        verbose_name = 'Lane Score'
        verbose_name_plural = 'Lane Scores'
    
    def __str__(self):
        return f"Lane {self.lane.lane_number} - Game {self.game.id}: {self.score} pts"
