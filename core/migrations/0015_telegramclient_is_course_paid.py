# Generated by Django 4.2.20 on 2025-06-16 03:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_broadcastaudio_custom_filename'),
    ]

    operations = [
        migrations.AddField(
            model_name='telegramclient',
            name='is_course_paid',
            field=models.BooleanField(default=False, verbose_name='Доступ к курсу'),
        ),
    ]
