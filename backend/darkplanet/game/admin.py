from django.contrib import admin

# Register your models here.
from .models import Player, Item, EVASuit, Room, RoomItem, Inventory, Monster

admin.site.register(Player)
admin.site.register(Item)
admin.site.register(EVASuit)
admin.site.register(Room)
admin.site.register(RoomItem)
admin.site.register(Inventory)
admin.site.register(Monster)