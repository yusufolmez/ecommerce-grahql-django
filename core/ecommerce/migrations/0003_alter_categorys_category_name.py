# Generated by Django 5.1.6 on 2025-02-19 11:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ecommerce', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='categorys',
            name='category_name',
            field=models.CharField(max_length=150, unique=True),
        ),
    ]
