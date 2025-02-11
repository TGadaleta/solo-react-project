# Generated by Django 5.1.5 on 2025-02-10 17:45

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
                ('weight', models.FloatField(default=0.0)),
                ('requires_energy', models.BooleanField(default=False)),
                ('max_energy', models.FloatField(blank=True, null=True)),
                ('current_energy', models.FloatField(blank=True, null=True)),
                ('energy_depletion_rate', models.FloatField(blank=True, null=True)),
                ('is_key_item', models.BooleanField(default=False)),
                ('is_wearable', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Room',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('first_time', models.BooleanField(default=True)),
                ('oxygen_level', models.FloatField(blank=True, null=True)),
                ('has_hazards', models.BooleanField(default=False)),
                ('hazard_description', models.TextField(blank=True, null=True)),
                ('has_monsters', models.BooleanField(default=False)),
                ('room_type', models.CharField(choices=[('ship', 'Ship Interior'), ('outside', 'Outside the Ship'), ('city', 'City Ruins')], default='ship', max_length=20)),
                ('descriptions', models.JSONField(default=dict)),
                ('connections', models.JSONField(default=dict)),
            ],
        ),
        migrations.CreateModel(
            name='EVASuit',
            fields=[
                ('item_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='game.item')),
                ('max_oxygen', models.FloatField(default=100.0)),
                ('current_oxygen', models.FloatField(default=100.0)),
                ('oxygen_depletion_rate', models.FloatField(default=2.0)),
            ],
            bases=('game.item',),
        ),
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('health', models.IntegerField(default=50, validators=[django.core.validators.MaxValueValidator(50)])),
                ('sanity', models.IntegerField(default=50, validators=[django.core.validators.MaxValueValidator(50)])),
                ('max_inventory_weight', models.FloatField(default=50.0)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('current_room', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='game.room')),
                ('eva_suit', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='game.evasuit')),
            ],
        ),
        migrations.CreateModel(
            name='Monster',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('description', models.TextField()),
                ('health', models.IntegerField(default=100)),
                ('sanity_attack', models.IntegerField(default=0)),
                ('physical_attack', models.IntegerField(default=0)),
                ('defense', models.IntegerField(default=0)),
                ('monster_type', models.CharField(choices=[('lurker', 'Lurker'), ('stalker', 'Stalker'), ('horror', 'Horror')], default='lurker', max_length=20)),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='monsters', to='game.room')),
            ],
        ),
        migrations.CreateModel(
            name='Inventory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(default=1)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game.item')),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inventory', to='game.player')),
            ],
            options={
                'unique_together': {('player', 'item')},
            },
        ),
        migrations.CreateModel(
            name='RoomItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='room_instances', to='game.item')),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='room_items', to='game.room')),
            ],
            options={
                'unique_together': {('room', 'item')},
            },
        ),
    ]
