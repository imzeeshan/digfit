import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0013_weight_reminder_days'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(choices=[('weight_log_overdue', 'Weight log overdue')], max_length=50)),
                ('title', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('icon', models.CharField(choices=[('scale-balanced', 'Scale'), ('bell', 'Bell')], default='bell', max_length=50)),
                ('action_url', models.CharField(blank=True, max_length=255)),
                ('action_label', models.CharField(default='View', max_length=64)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('is_read', models.BooleanField(default=False)),
                ('is_dismissed', models.BooleanField(default=False)),
                ('email_sent_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Notification',
                'verbose_name_plural': 'Notifications',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(
                        fields=['user', 'is_dismissed', '-created_at'],
                        name='dashboard_n_user_id_8f3a2c_idx',
                    ),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name='notification',
            constraint=models.UniqueConstraint(fields=('user', 'notification_type'), name='unique_notification_per_user_type'),
        ),
    ]
