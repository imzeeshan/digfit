from django.conf import settings
from django.core.mail import send_mail
from django.tasks import task


@task
def send_subscription_confirmation_email(user_email, plan_name):
    """Send confirmation email when a user subscribes to a plan."""
    send_mail(
        subject=f"Subscription Confirmed - {plan_name}",
        message=f"Your subscription to the {plan_name} plan has been confirmed. Thank you!",
        from_email=settings.EMAIL_HOST_USER or None,
        recipient_list=[user_email],
    )


@task
def send_subscription_cancellation_email(user_email):
    """Send notification email when a user cancels their subscription."""
    send_mail(
        subject="Subscription Cancelled",
        message="Your subscription has been cancelled. We're sorry to see you go!",
        from_email=settings.EMAIL_HOST_USER or None,
        recipient_list=[user_email],
    )


@task
def send_weight_reminder_email(user_email, title, message, action_path):
    """Email the user when their weight log is overdue (if notify_updates is on)."""
    from django.contrib.sites.models import Site

    site = Site.objects.get_current()
    base = f'https://{site.domain}' if not site.domain.startswith('http') else site.domain
    action_url = f'{base.rstrip("/")}{action_path}'
    send_mail(
        subject=title,
        message=f'{message}\n\nLog your weight: {action_url}',
        from_email=settings.EMAIL_HOST_USER or None,
        recipient_list=[user_email],
    )


@task
def send_trial_started_email(user_email):
    """Send welcome email when a user starts a trial."""
    send_mail(
        subject="Welcome to Your Free Trial!",
        message="Your 14-day free trial has started. Explore all premium features!",
        from_email=settings.EMAIL_HOST_USER or None,
        recipient_list=[user_email],
    )
