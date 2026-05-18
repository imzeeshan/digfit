from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.dashboard.models import UserSettings, Weight
from apps.dashboard.notifications import sync_user_notifications


@receiver(post_save, sender=Weight)
@receiver(post_delete, sender=Weight)
def refresh_notifications_on_weight_change(sender, instance, **kwargs):
    sync_user_notifications(instance.user)


@receiver(post_save, sender=UserSettings)
def refresh_notifications_on_settings_change(sender, instance, **kwargs):
    sync_user_notifications(instance.user)
