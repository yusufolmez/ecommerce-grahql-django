# Generated by Django 5.1.6 on 2025-02-20 07:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ecommerce', '0008_remove_cartitem_product_cartitem_product_variant'),
    ]

    operations = [
        migrations.AddField(
            model_name='productvariants',
            name='stock',
            field=models.PositiveIntegerField(default=1),
        ),
    ]
