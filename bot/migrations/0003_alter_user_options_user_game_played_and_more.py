# Generated by Django 4.2.5 on 2024-12-16 00:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0002_remove_user_user_name_user_username_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={},
        ),
        migrations.AddField(
            model_name='user',
            name='game_played',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='user',
            name='highest_score',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='user',
            name='full_name',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
