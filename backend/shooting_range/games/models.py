from django.db import models
from django.conf import settings
from django.utils import timezone


class GameMode(models.TextChoices):
    INDIVIDUAL = 'individual', 'Individual Lane Mode'
    ALL_LANES = 'all_lanes', 'All Lanes Mode'


class GameStatus(models.TextChoices):
    IDLE = 'idle', 'Idle'
    COUNTDOWN = 'countdown', 'Countdown'
    ACTIVE = 'active', 'Active'
    PAUSED = 'paused', 'Paused'
    ENDED = 'ended', 'Ended'


class GameConfiguration(models.Model):
    """Stores game configuration presets."""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
    
    # Game timing
    duration = models.PositiveIntegerField(
        default=60,
        help_text="Game duration in seconds"
    )
    countdown_seconds = models.PositiveIntegerField(
        default=3,
        help_text="Countdown seconds before game starts"
    )
    
    # Scoring
    win_score = models.PositiveIntegerField(
        default=1000,
        help_text="Score at which game ends early (optional)"
    )
    use_win_score = models.BooleanField(
        default=False,
        help_text="End game when any lane reaches win_score"
    )
    
    # Sensor scoring configuration
    sensor_points = models.JSONField(
        default=dict,
        help_text="Points per sensor, e.g. {'head': 100, 'chest': 50}"
    )
    use_accuracy_multiplier = models.BooleanField(
        default=True,
        help_text="Multiply score by accuracy (0.0-1.0)"
    )
    
    # Effects
    enable_sound = models.BooleanField(default=True)
    enable_visual_effects = models.BooleanField(default=True)
    
    # Branding
    primary_color = models.CharField(max_length=7, default='#00FF00')
    secondary_color = models.CharField(max_length=7, default='#000000')
    logo_url = models.URLField(blank=True, default='')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Game Configuration'
        verbose_name_plural = 'Game Configurations'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Set default sensor points if not provided
        if not self.sensor_points:
            self.sensor_points = {
                'head': 100,
                'chest': 50,
                'stomach': 30,
                'left_leg': 20,
                'right_leg': 20,
            }
        super().save(*args, **kwargs)


class Game(models.Model):
    """Represents a game session."""
    
    game_id = models.CharField(max_length=36, unique=True, db_index=True)
    mode = models.CharField(
        max_length=20,
        choices=GameMode.choices,
        default=GameMode.INDIVIDUAL
    )
    status = models.CharField(
        max_length=20,
        choices=GameStatus.choices,
        default=GameStatus.IDLE
    )
    
    # Configuration
    configuration = models.ForeignKey(
        GameConfiguration,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='games'
    )
    
    # Timing
    duration = models.PositiveIntegerField(default=60)
    countdown_seconds = models.PositiveIntegerField(default=3)
    win_score = models.PositiveIntegerField(default=1000)
    use_win_score = models.BooleanField(default=False)
    
    # Active lanes for this game
    active_lanes = models.ManyToManyField('lanes.Lane', related_name='games', blank=True)
    
    # Winner
    winner_lane = models.ForeignKey(
        'lanes.Lane',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='won_games'
    )
    
    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Game'
        verbose_name_plural = 'Games'
    
    def __str__(self):
        return f"Game {self.game_id} ({self.get_status_display()})"
    
    @property
    def is_running(self):
        return self.status == GameStatus.ACTIVE
    
    @property
    def remaining_time(self):
        """Calculate remaining game time in seconds."""
        if not self.started_at:
            return self.duration
        if self.status != GameStatus.ACTIVE:
            return self.duration
        
        elapsed = (timezone.now() - self.started_at).total_seconds()
        remaining = self.duration - elapsed
        return max(0, int(remaining))
    
    @property
    def winner_lane_number(self):
        """Get the lane number of the winner."""
        if self.winner_lane:
            return self.winner_lane.lane_number
        return None
    
    def start(self):
        """Start the game."""
        self.status = GameStatus.ACTIVE
        self.started_at = timezone.now()
        self.save()
    
    def end(self):
        """End the game."""
        self.status = GameStatus.ENDED
        self.ended_at = timezone.now()
        self.save()
    
    def get_score_for_position(self, position: str, accuracy: float) -> int:
        """Calculate score for a hit based on position and accuracy."""
        if not self.configuration:
            return 0
        
        base_points = self.configuration.sensor_points.get(position, 0)
        
        if self.configuration.use_accuracy_multiplier:
            return int(base_points * accuracy)
        
        return base_points


class HitEvent(models.Model):
    """Records individual hit events during a game."""
    
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='hits')
    lane = models.ForeignKey('lanes.Lane', on_delete=models.CASCADE, related_name='hit_events')
    
    # Hit details
    position = models.CharField(max_length=50)
    accuracy = models.FloatField()
    raw_strength = models.PositiveIntegerField(default=0)
    score = models.PositiveIntegerField(default=0)
    
    # Timestamps
    event_timestamp = models.DateTimeField(db_index=True)
    received_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-event_timestamp']
        verbose_name = 'Hit Event'
        verbose_name_plural = 'Hit Events'
        indexes = [
            models.Index(fields=['game', '-event_timestamp']),
            models.Index(fields=['lane', '-event_timestamp']),
        ]
    
    def __str__(self):
        return f"Hit: Lane {self.lane.lane_number} - {self.position} ({self.score} pts)"
