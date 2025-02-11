from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator

# ✅ Player Model
class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    health = models.IntegerField(default=50, validators=[MaxValueValidator(50)])
    sanity = models.IntegerField(default=50, validators=[MaxValueValidator(50)])
    current_room = models.ForeignKey("Room", on_delete=models.SET_NULL, null=True)
    max_inventory_weight = models.FloatField(default=50.0)
    eva_suit = models.OneToOneField("EVASuit", on_delete=models.SET_NULL, null=True, blank=True)  # Equipped EVA Suit

    def get_total_inventory_weight(self):
        """Calculate the total weight of all items in the inventory."""
        return sum(inventory_item.get_total_weight() for inventory_item in self.inventory.all())

    def is_overburdened(self):
        """Check if the player is carrying too much weight."""
        return self.get_total_inventory_weight() > self.max_inventory_weight

    def consume_oxygen(self, base_amount):
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
        suit_status = f" - Wearing {self.eva_suit.name}" if self.eva_suit else " - No EVA Suit Equipped"
        return f"{self.user.username} (Health: {self.health}, Sanity: {self.sanity}, Inventory Weight: {self.get_total_inventory_weight()}/{self.max_inventory_weight} kg){status}{suit_status}"

# ✅ Item Model
class Item(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    weight = models.FloatField(default=0.0)  # Weight of the item
    requires_energy = models.BooleanField(default=False)  # Does this item need energy?
    max_energy = models.FloatField(null=True, blank=True)  # Maximum energy capacity
    current_energy = models.FloatField(null=True, blank=True)  # Current energy level
    energy_depletion_rate = models.FloatField(null=True, blank=True)  # How much energy is lost per use
    is_key_item = models.BooleanField(default=False)
    is_wearable = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        """Ensure energy values are only set if the item requires energy."""
        if not self.requires_energy:
            self.max_energy = None
            self.current_energy = None
            self.energy_depletion_rate = None
        elif self.current_energy is None:
            self.current_energy = self.max_energy  # Default to full charge
        super().save(*args, **kwargs)

    def use_energy(self):
        """Depletes energy based on depletion rate and prevents negative values."""
        if self.requires_energy and self.current_energy is not None:
            if self.energy_depletion_rate is None:
                return f"{self.name} cannot be used because depletion rate is not set."
            self.current_energy -= self.energy_depletion_rate
            self.current_energy = max(self.current_energy, 0)  # Prevents negative energy
            self.save()
            return f"{self.name} used. Remaining Energy: {self.current_energy}/{self.max_energy}"
        return f"{self.name} does not use energy."

    def recharge(self):
        """Restores energy to full."""
        if self.requires_energy and self.max_energy is not None:
            self.current_energy = self.max_energy
            self.save()
            return f"{self.name} recharged to full energy."
        return f"{self.name} does not require charging."

    def __str__(self):
        return f"{self.name} (Weight: {self.weight} kg, Energy: {self.current_energy}/{self.max_energy if self.requires_energy else 'N/A'})"

# ✅ EVASuit Model
class EVASuit(Item):
    max_oxygen = models.FloatField(default=100.0)
    current_oxygen = models.FloatField(default=100.0)
    oxygen_depletion_rate = models.FloatField(default=2.0)

    def consume_oxygen(self, base_amount=0):
        """Reduces EVA Suit's oxygen level based on activity."""
        depletion = self.oxygen_depletion_rate + base_amount
        self.current_oxygen = max(self.current_oxygen - depletion, 0)  # Prevent negative oxygen
        self.save()
        return f"{self.name} oxygen reduced by {depletion:.2f}. Remaining: {self.current_oxygen:.2f}%"

    def recharge_oxygen(self, environment_oxygen_level):
        """Gradually recharges oxygen in full-oxygen environments."""
        if environment_oxygen_level == 100.0:
            self.current_oxygen = min(self.current_oxygen + 5.0, self.max_oxygen)
            self.save()
            return f"{self.name} oxygen increased by 5%. Remaining: {self.current_oxygen:.2f}%"
        return f"{self.name} cannot recharge. Low oxygen environment."

    def __str__(self):
        return f"{self.name} (Oxygen: {self.current_oxygen}/{self.max_oxygen})"

# ✅ Room Model
class Room(models.Model):
    ROOM_TYPES = [
        ("ship", "Ship Interior"),
        ("outside", "Outside the Ship"),
        ("city", "City Ruins"),
    ]

    name = models.CharField(max_length=255, unique=True)
    first_time = models.BooleanField(default=True)
    oxygen_level = models.FloatField(null=True, blank=True)  # % of breathable air
    has_hazards = models.BooleanField(default=False)
    hazard_description = models.TextField(blank=True, null=True)
    has_monsters = models.BooleanField(default=False)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default="ship")
    descriptions = models.JSONField(default=dict)
    connections = models.JSONField(default=dict)

    def get_description(self):
        """Return appropriate description based on visit status."""
        return self.descriptions.get("first_time", "Unknown area.") if self.first_time else self.descriptions.get("repeat", "Looks the same as before.")

    def get_adjacent_rooms(self):
        """Return a dictionary of connected rooms."""
        return self.connections

    def __str__(self):
        return (
            f"{self.name} (Type: {self.room_type}, Oxygen: {self.oxygen_level if self.oxygen_level is not None else 'No Atmosphere'}, "
            f"Hazard: {'Yes' if self.has_hazards else 'No'}, Monsters: {'Yes' if self.has_monsters else 'No'})"
        )

# ✅ RoomItem Model
class RoomItem(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="room_items")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="room_instances")
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("room", "item")

    def __str__(self):
        return f"{self.quantity}x {self.item.name} in {self.room.name}"

# ✅ Inventory Model
class Inventory(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="inventory")
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    class Meta:
        unique_together = ("player", "item")

    def save(self, *args, **kwargs):
        """Prevent multiple EVA Suits from being stored in inventory."""
        if self.item.is_wearable and self.item.is_key_item:
            if Inventory.objects.filter(player=self.player, item__is_wearable=True).exists():
                raise ValueError("Cannot store multiple EVA Suits.")
        super().save(*args, **kwargs)

    def get_total_weight(self):
        """Calculate total weight of this inventory item (item weight * quantity)."""
        return self.item.weight * self.quantity

    def __str__(self):
        return f"{self.player.user.username} has {self.quantity}x {self.item.name} (Total Weight: {self.get_total_weight()} kg)"


class Monster(models.Model):
    MONSTER_TYPES = [
        ("lurker", "Lurker"),  # Stays hidden until attacked
        ("stalker", "Stalker"),  # Follows the player silently
        ("horror", "Horror"),  # Aggressive entity
    ]

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField()
    health = models.IntegerField(default=100)
    sanity_attack = models.IntegerField(default=0)  # How much sanity it drains
    physical_attack = models.IntegerField(default=0)  # Physical damage dealt
    defense = models.IntegerField(default=0)  # Damage reduction from attacks
    monster_type = models.CharField(max_length=20, choices=MONSTER_TYPES, default="lurker")

    # Where the monster currently resides
    room = models.ForeignKey("Room", on_delete=models.CASCADE, related_name="monsters")

    def take_damage(self, amount):
        """
        Reduces monster health considering its defense.
        - Defense reduces incoming damage.
        """
        actual_damage = max(amount - self.defense, 1)  # Minimum damage is 1
        self.health = max(self.health - actual_damage, 0)  # Prevents negative health
        self.save()
        return f"{self.name} took {actual_damage} damage! Remaining HP: {self.health}"

    def attack(self, player):
        """
        Attacks the player, dealing both physical and sanity damage.
        """
        player.health = max(player.health - self.physical_attack, 0)
        player.sanity = max(player.sanity - self.sanity_attack, 0)
        player.save()
        return f"{self.name} attacks! {player.user.username} loses {self.physical_attack} HP and {self.sanity_attack} sanity!"

    def is_alive(self):
        """Returns True if the monster is still alive."""
        return self.health > 0

    def __str__(self):
        return f"{self.name} (Type: {self.monster_type}, HP: {self.health}, Atk: {self.physical_attack}, Sanity Drain: {self.sanity_attack})"


