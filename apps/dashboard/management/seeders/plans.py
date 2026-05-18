from apps.dashboard.models import SubscriptionPlan


def seed_plans(stdout, style):
    """Create subscription plans; return slug -> plan mapping."""
    plans_data = [
        {
            'name': 'Free',
            'slug': 'free',
            'description': 'Get started with the basics',
            'price': 0,
            'interval': 'monthly',
            'features': ['Basic access', 'Community support', '1 project'],
        },
        {
            'name': 'Pro',
            'slug': 'pro',
            'description': 'For growing teams and businesses',
            'price': 9.99,
            'interval': 'monthly',
            'features': [
                'Everything in Free',
                'Priority support',
                'API access',
                '10 projects',
                'Analytics',
            ],
        },
        {
            'name': 'Pro Annual',
            'slug': 'pro-yearly',
            'description': 'Pro plan billed yearly',
            'price': 99.99,
            'interval': 'yearly',
            'features': [
                'Everything in Pro',
                '2 months free vs monthly',
                'Priority support',
                'API access',
            ],
        },
        {
            'name': 'Enterprise',
            'slug': 'enterprise',
            'description': 'For large-scale operations',
            'price': 49.99,
            'interval': 'monthly',
            'features': [
                'Everything in Pro',
                'Dedicated support',
                'Custom integrations',
                'Unlimited projects',
                'SLA guarantee',
            ],
        },
    ]

    plans = {}
    for plan_data in plans_data:
        plan, created = SubscriptionPlan.objects.get_or_create(
            slug=plan_data['slug'],
            defaults=plan_data,
        )
        plans[plan.slug] = plan
        status = 'created' if created else 'already exists'
        stdout.write(style.SUCCESS(f'Plan "{plan.name}" {status}'))

    return plans
