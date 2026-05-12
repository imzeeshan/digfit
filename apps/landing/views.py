from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods


@require_http_methods(['GET'])
def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "",
        "Sitemap: https://yourdomain.com/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


@require_http_methods(['GET'])
def home(request):
    features = [
        {
            'icon': 'utensils',
            'title': 'Personal meal plans',
            'description': 'Weekly recipes set to your goals, dietary needs, and what\'s already in the fridge.',
        },
        {
            'icon': 'clipboard-check',
            'title': 'Effortless logging',
            'description': 'Snap, talk, or type — your DigFit journal captures bites in under five seconds flat.',
        },
        {
            'icon': 'bell',
            'title': 'Nudge engine',
            'description': 'Like a friend — a clever, encouraging one — who texts you at the right time.',
        },
        {
            'icon': 'list-check',
            'title': 'Smart Grocery Lists',
            'description': 'Your fridge + your plan = one smart, no-nonsense shopping trip each week.',
        },
        {
            'icon': 'chart-line',
            'title': 'Nutrition that adapts',
            'description': 'Macros, micros, goals and simple adjustments in real-time — built to fit life, not the other way.',
        },
        {
            'icon': 'trophy',
            'title': 'Habit building',
            'description': 'Tiny streaks, smart goals. Gentle cues to stay consistent, one day at a time.',
        },
    ]

    steps = [
        {
            'number': '01',
            'title': 'Tell us about you',
            'description': 'Goals, allergies, lifestyle — we listen carefully.',
        },
        {
            'number': '02',
            'title': 'Get your plan',
            'description': 'A simple plan built around your taste and your life.',
        },
        {
            'number': '03',
            'title': 'Track your meals',
            'description': 'Snap a photo or let our AI do the heavy lifting for you.',
        },
        {
            'number': '04',
            'title': 'Stay on track',
            'description': 'Smart nudges and progress tracking to keep you going.',
        },
    ]

    return render(request, 'landing/home.html', {
        'features': features,
        'steps': steps,
    })


@require_http_methods(['GET'])
def pricing(request):
    return render(request, 'landing/pricing.html')


@require_http_methods(['GET'])
def features(request):
    return render(request, 'landing/features.html')
