from django.db import models
from django.contrib.auth.models import User

# ✅ Player Model
class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    HEALTH_STATUS = ['healthy', 'injured', 'critical', 'near death', 'dead']
    SANITY_STATUS = ['stable', 'unsettled', 'disturbed', 'broken', 'insane']

    current_health = models.CharField(max_length=15, choices=[(h, h.capitalize()) for h in HEALTH_STATUS], default='healthy')
    current_sanity = models.CharField(max_length=15, choices=[(s, s.capitalize()) for s in SANITY_STATUS], default='stable')

    current_room = models.ForeignKey("Room", on_delete=models.SET_NULL, null=True)
    max_inventory_weight = models.FloatField(default=50.0)
    eva_suit = models.ForeignKey('EVASuit', on_delete=models.SET_NULL, null=True, blank=True)

    def check_game_over(self, custom_message=None):
        """Centralized game over check with EVA Suit safeguard."""
        if not self.eva_suit:
            return None  # ✅ Prevents AttributeError if eva_suit is None
        if self.current_health == "dead":
            return custom_message or "Your body fails you. The Abyss claims you."
        if self.current_sanity == "insane":
            return custom_message or "The whispers consume you. The Abyss has taken you."
        
        if self.eva_suit and (self.eva_suit.current_status == "destroyed" or self.eva_suit.current_oxygen == 0):
            return custom_message or "The EVA Suit fails. Your final breath escapes into the void. The Abyss claims you."
        
        return None

    def take_damage(self, steps=1, custom_message=None):
        self.current_health = self.progress_status(self.current_health, self.HEALTH_STATUS, steps)
        self.save()
        return self.check_game_over(custom_message) or f"You are now {self.current_health.upper()}."

    def lose_sanity(self, steps=1, custom_message=None):
        self.current_sanity = self.progress_status(self.current_sanity, self.SANITY_STATUS, steps)
        self.save()
        return self.check_game_over(custom_message) or f"You are now {self.current_sanity.upper()}."

    def progress_status(self, current_status, progression_list, steps):
        if not progression_list:
            return current_status  # ✅ Safeguard for empty lists
        try:
            current_index = progression_list.index(current_status)
            new_index = min(current_index + steps, len(progression_list) - 1)
            return progression_list[new_index]
        except ValueError:
            return current_status
    
    def regress_status(self, current_status, progression_list, steps):
        if not progression_list:
            return current_status  # ✅ Safeguard for empty lists
        try:
            current_index = progression_list.index(current_status)
            new_index = max(current_index - steps, 0)
            return progression_list[new_index]
        except ValueError:
            return current_status

    def __str__(self):
        return f"{self.user.username} (Health: {self.current_health}, Sanity: {self.current_sanity})"


# ✅ EVASuit Model
class EVASuit(models.Model):
    EVA_STATUS = ["green", "yellow", "orange", "red", "destroyed"]

    STATUS_OXYGEN_DEPLETION = {
        "green": 0.5,
        "yellow": 1.0,
        "orange": 2.0,
        "red": 5.0
    }

    current_status = models.CharField(max_length=10, choices=[(s, s.capitalize()) for s in EVA_STATUS], default="green")
    max_oxygen = models.FloatField(default=100.0)
    current_oxygen = models.FloatField(default=100.0)
    is_in_station = models.BooleanField(default=True)
    is_worn = models.BooleanField(default=False)

    def consume_oxygen(self, player, action_amount=0):
        depletion = self.STATUS_OXYGEN_DEPLETION.get(self.current_status, 0) + action_amount  # ✅ Added safeguard
        self.current_oxygen = max(self.current_oxygen - depletion, 0)
        self.save()

        if self.current_oxygen == 0 or self.current_status == "destroyed":
            return player.check_game_over()
        
        return f"EVA Suit oxygen reduced by {depletion:.1f}. Remaining: {self.current_oxygen:.1f}%"

    def progress_status(self, steps=1):
        current_index = self.EVA_STATUS.index(self.current_status)
        new_index = min(current_index + steps, len(self.EVA_STATUS) - 1)
        self.current_status = self.EVA_STATUS[new_index]
        self.save()
        return f"EVA Suit status degraded to {self.current_status.upper()}."

    def regress_status(self, steps=1):
        current_index = self.EVA_STATUS.index(self.current_status)
        new_index = max(current_index - steps, 0)
        self.current_status = self.EVA_STATUS[new_index]
        self.save()
        return f"EVA Suit repaired to {self.current_status.upper()}."

    def __str__(self):
        return f"EVA Suit (Status: {self.current_status}, Oxygen: {self.current_oxygen}/{self.max_oxygen})"


# ✅ Item Model
class Item(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    weight = models.FloatField(default=0.0)
    requires_energy = models.BooleanField(default=False)
    max_energy = models.FloatField(null=True, blank=True)
    current_energy = models.FloatField(null=True, blank=True)
    energy_depletion_rate = models.FloatField(null=True, blank=True)
    is_key_item = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.requires_energy:
            self.max_energy = None
            self.current_energy = None
            self.energy_depletion_rate = None
        elif self.current_energy is None:
            self.current_energy = self.max_energy
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (Weight: {self.weight} kg, Energy: {self.current_energy}/{self.max_energy if self.requires_energy else 'N/A'})"


# ✅ Inventory Model
class Inventory(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="inventory")
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    class Meta:
        unique_together = ("player", "item")

    def save(self, *args, **kwargs):
        if self.item.is_key_item and Inventory.objects.filter(player=self.player, item=self.item).exclude(id=self.id).exists():
            # ✅ Excludes the current item from the query during updates
            raise ValueError(f"You cannot carry more than one {self.item.name}.")
        super().save(*args, **kwargs)

    def get_total_weight(self):
        return self.item.weight * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.item.name} (Total Weight: {self.get_total_weight()} kg)"


# ✅ RoomItem Model
class RoomItem(models.Model):
    room = models.ForeignKey("Room", on_delete=models.CASCADE, related_name="room_items")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="room_instances")
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("room", "item")

    def __str__(self):
        return f"{self.quantity}x {self.item.name} in {self.room.name}"


# ✅ Room Model
class Room(models.Model):
    ROOM_TYPES = [
        ("interior", "Ship Interior"),
        ("exterior", "Ship Exterior"),
        ("wasteland", "Wasteland"),
        ("city", "City Ruins"),
    ]

    name = models.CharField(max_length=255, unique=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default="interior")
    oxygen_level = models.FloatField(null=True, blank=True)

    descriptions = models.JSONField(default=dict)
    connections = models.JSONField(default=dict)

    hazards = models.ManyToManyField('Hazard', blank=True, related_name="rooms")

    def save(self, *args, **kwargs):
        if self._state.adding and not self.connections:  # ✅ Only sets defaults when creating a new room
            if self.room_type == "interior":
                default_connections = {
                    "forward": None,
                    "aft": None,
                    "starboard": None,
                    "port": None,
                    "up": None,
                    "down": None
                }
            else:
                default_connections = {
                    "north": None,
                    "south": None,
                    "east": None,
                    "west": None,
                    "up": None,
                    "down": None
                }
            self.connections = default_connections
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (Type: {self.room_type}, Oxygen: {self.oxygen_level if self.oxygen_level is not None else 'No Atmosphere'})"


# ✅ Hazard Model
class Hazard(models.Model):
    HAZARD_TYPES = [
        ("radiation", "Radiation"),
        ("toxic_gas", "Toxic Gas"),
        ("extreme_heat", "Extreme Heat"),
        ("extreme_cold", "Extreme Cold"),
        ("unstable_terrain", "Unstable Terrain"),
        ("psychic_disturbance", "Psychic Disturbance"),
        ("void_anomaly", "Void Anomaly"),
    ]

    name = models.CharField(max_length=100, unique=True)
    hazard_type = models.CharField(max_length=20, choices=HAZARD_TYPES)
    description = models.TextField()
    damage_per_turn = models.IntegerField(default=1)
    affects_sanity = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.hazard_type}) - {self.description[:50]}..."
