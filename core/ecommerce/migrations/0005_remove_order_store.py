# Generated by Django 5.1.6 on 2025-02-24 09:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ecommerce', '0004_order_store'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='store',
        ),
    ]
