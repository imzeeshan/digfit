from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0003_hash_api_keys'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersettings',
            name='ollama_host',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='usersettings',
            name='ollama_model',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
    ]
