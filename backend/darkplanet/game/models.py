from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator

# ✅ Player Model
class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    sanity = models.IntegerField(default=50, validators=[MaxValueValidator(50)])
    current_room = models.ForeignKey("Room", on_delete=models.SET_NULL, null=True)
    max_inventory_weight = models.FloatField(default=50.0)
    eva_suit = models.ForeignKey('EVASuit', on_delete=models.SET_NULL, null=True, blank=True)

    def get_total_inventory_weight(self):
        """Calculate the total weight of all items in the inventory."""
        return sum(inventory_item.get_total_weight() for inventory_item in self.inventories.all())

    def is_overburdened(self):
        """Check if the player is carrying too much weight."""
        return self.get_total_inventory_weight() > self.max_inventory_weight

    def consume_oxygen(self, base_amount=0):
        """Reduces oxygen from EVA Suit or directly from Player."""
        if self.eva_suit:
            return self.eva_suit.consume_oxygen(base_amount)
        return f"{self.user.username} is suffocating! No EVA suit equipped."

    def recharge_suit(self):
        """Triggers EVA Suit to recharge based on current room's oxygen level."""
        if self.eva_suit and self.current_room:
            return self.eva_suit.recharge_oxygen(self.current_room.oxygen_level)
        return f"No EVA Suit equipped or unknown room conditions."

    def __str__(self):
        status = " (Overburdened)" if self.is_overburdened() else ""
        return f"{self.user.username} (Sanity: {self.sanity}, Inventory Weight: {self.get_total_inventory_weight()}/{self.max_inventory_weight} kg){status}"

# ✅ Item Model
class Item(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    weight = models.FloatField(default=0.0)  # Weight of the item
    requires_energy = models.BooleanField(default=False)  # Does this item need energy?
    max_energy = models.FloatField(null=True, blank=True)  # Maximum energy capacity
    current_energy = models.FloatField(null=True, blank=True)  # Current energy level
    energy_depletion_rate = models.FloatField(null=True, blank=True)  # How much energy is lost per use
    is_key_item = models.BooleanField(default=False)  # Determines if only one can be held

    def save(self, *args, **kwargs):
        """Ensure energy values are only set if the item requires energy."""
        if not self.requires_energy:
            self.max_energy = None
            self.current_energy = None
            self.energy_depletion_rate = None
        elif self.current_energy is None:
            self.current_energy = self.max_energy  # Default to full charge
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (Weight: {self.weight} kg, Energy: {self.current_energy}/{self.max_energy if self.requires_energy else 'N/A'})"

# ✅ Inventory Model
class Inventory(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="inventories")
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    class Meta:
        unique_together = ("player", "item")

    def save(self, *args, **kwargs):
        """Prevent multiple key items from being stored in inventory."""
        if self.item.is_key_item and Inventory.objects.filter(player=self.player, item=self.item).exists():
            raise ValueError(f"{self.player.user.username} cannot carry more than one {self.item.name}.")
        super().save(*args, **kwargs)

    def get_total_weight(self):
        """Calculate total weight of this inventory item (item weight * quantity)."""
        return self.item.weight * self.quantity

    def __str__(self):
        return f"{self.player.user.username} has {self.quantity}x {self.item.name} (Total Weight: {self.get_total_weight()} kg)"

# ✅ RoomItem Model
class RoomItem(models.Model):
    room = models.ForeignKey("Room", on_delete=models.CASCADE, related_name="room_items")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="room_instances")
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("room", "item")

    def __str__(self):
        return f"{self.quantity}x {self.item.name} in {self.room.name}"

# ✅ EVASuit Model
class EVASuit(models.Model):
    EVA_STATUS = [
        ("green", "Green"),
        ("yellow", "Yellow"),
        ("orange", "Orange"),
        ("red", "Red")
    ]
    
    STATUS_OXYGEN_DEPLETION = {
        'green': 0.5,
        'yellow': 1.0,
        'orange': 2.0,
        'red': 5.0
    }

    STATUS_PROGRESSION = {
        "green": "yellow",
        "yellow": "orange",
        "orange": "red",
        "red": "red"  # Red is the worst condition
    }

    max_oxygen = models.FloatField(default=100.0)
    current_oxygen = models.FloatField(default=100.0)
    is_in_station = models.BooleanField(default=True)
    is_worn = models.BooleanField(default=False)
    current_status = models.CharField(max_length=10, choices=EVA_STATUS, default='green')

    @property
    def oxygen_depletion_rate(self):
        return self.STATUS_OXYGEN_DEPLETION.get(self.current_status, 0.5)

    def degrade_status(self):
        """Degrades the EVA suit's status when taking damage."""
        self.current_status = self.STATUS_PROGRESSION[self.current_status]
        self.save()
        return f"EVA Suit status degraded to {self.current_status.upper()}."

    def consume_oxygen(self, action_amount=0):
        """Reduces EVA Suit's oxygen level based on activity."""
        depletion = self.oxygen_depletion_rate + action_amount
        self.current_oxygen = max(self.current_oxygen - depletion, 0)  # Prevent negative oxygen
        self.save()
        return f"EVA Suit oxygen reduced by {depletion:.1f}. Remaining: {self.current_oxygen:.1f}%"

    def __str__(self):
        return f"EVA Suit (Status: {self.current_status}, Oxygen: {self.current_oxygen}/{self.max_oxygen})"

# ✅ Room Model
class Room(models.Model):
    ROOM_TYPES = [
        ("ship", "Ship Interior"),
        ("outside", "Outside the Ship"),
        ("city", "City Ruins"),
    ]

    name = models.CharField(max_length=255, unique=True)
    first_time = models.BooleanField(default=True)
    oxygen_level = models.FloatField(null=True, blank=True)
    has_hazards = models.BooleanField(default=False)
    hazard_description = models.TextField(blank=True, null=True)
    has_monsters = models.BooleanField(default=False)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default="ship")

    # ✅ Fix: Use `dict` as default (prevents migration error)
    descriptions = models.JSONField(default=dict)
    connections = models.JSONField(default=dict)

    def save(self, *args, **kwargs):
        """Ensure `connections` always has the correct default structure."""
        default_connections = {
            "north": None,
            "south": None,
            "east": None,
            "west": None,
            "up": None,
            "down": None
        }
        # ✅ If `connections` is empty, apply the default structure
        if not self.connections:
            self.connections = default_connections

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (Type: {self.room_type}, Oxygen: {self.oxygen_level if self.oxygen_level is not None else 'No Atmosphere'})"

# ✅ Monster Model
class Monster(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField()
    sanity_attack = models.IntegerField(default=0)
    monster_type = models.CharField(max_length=20, default="lurker")
    room = models.ForeignKey("Room", on_delete=models.CASCADE, related_name="monsters")

    def attack(self, player):
        """Monster attack degrades the EVA Suit status instead of health."""
        return f"{self.name} attacks! {player.eva_suit.degrade_status() if player.eva_suit else 'No EVA Suit! Direct exposure to the environment.'}"
