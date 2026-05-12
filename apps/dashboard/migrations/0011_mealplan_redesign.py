"""
Redesign MealPlan: convert from flat single-meal rows to a container model
with child MealEntry records.  Existing MealPlan rows are migrated into
MealEntry rows attached to a new parent MealPlan.
"""
import django.db.models
from django.db import migrations, models


def migrate_existing_mealplans(apps, schema_editor):
    """Move old flat MealPlan data into MealEntry rows."""
    MealPlan = apps.get_model('dashboard', 'MealPlan')
    MealEntry = apps.get_model('dashboard', 'MealEntry')

    for plan in MealPlan.objects.all():
        old_meal_type = plan._old_meal_type or 'breakfast'
        old_meal_name = plan._old_meal_name or ''
        old_foods = plan._old_foods_json if plan._old_foods_json else []
        old_cal = plan._old_total_calories or 0
        old_protein = plan._old_total_protein or 0
        old_carbs = plan._old_total_carbs or 0
        old_fat = plan._old_total_fat or 0

        if not plan.title:
            plan.title = old_meal_name or f'{old_meal_type.title()} plan'
            plan.save(update_fields=['title'])

        mapped_type = old_meal_type if old_meal_type in (
            'breakfast', 'lunch', 'dinner',
        ) else 'breakfast'

        MealEntry.objects.create(
            meal_plan=plan,
            meal_type=mapped_type,
            day_number=1,
            title=old_meal_name or old_meal_type.title(),
            foods_json=old_foods,
            calories=old_cal,
            protein=old_protein,
            carbs=old_carbs,
            fat=old_fat,
            sort_order=0,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0010_fix_mealplan_index_name'),
    ]

    operations = [
        # --- Phase 1: Add new fields to MealPlan (nullable / with defaults) ---
        migrations.AddField(
            model_name='mealplan',
            name='title',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='mealplan',
            name='daily_calorie_target',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='mealplan',
            name='daily_protein_target',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True),
        ),
        migrations.AddField(
            model_name='mealplan',
            name='daily_carbs_target',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True),
        ),
        migrations.AddField(
            model_name='mealplan',
            name='daily_fat_target',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True),
        ),
        migrations.AddField(
            model_name='mealplan',
            name='daily_water_target_ml',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='mealplan',
            name='dietary_preference',
            field=models.CharField(
                choices=[
                    ('none', 'No Preference'),
                    ('vegetarian', 'Vegetarian'),
                    ('vegan', 'Vegan'),
                    ('keto', 'Keto'),
                    ('high_protein', 'High Protein'),
                    ('paleo', 'Paleo'),
                    ('mediterranean', 'Mediterranean'),
                ],
                default='none',
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='mealplan',
            name='allergies_restrictions',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='mealplan',
            name='supplements',
            field=models.JSONField(blank=True, default=list),
        ),

        # --- Phase 2: Update ordering BEFORE renaming fields ---
        migrations.AlterModelOptions(
            name='mealplan',
            options={
                'ordering': ['-start_date'],
                'verbose_name': 'Meal Plan',
                'verbose_name_plural': 'Meal Plans',
            },
        ),

        # --- Phase 3: Create MealEntry table ---
        migrations.CreateModel(
            name='MealEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('meal_type', models.CharField(
                    choices=[
                        ('breakfast', 'Breakfast'),
                        ('mid_morning_snack', 'Mid-morning Snack'),
                        ('lunch', 'Lunch'),
                        ('evening_snack', 'Evening Snack'),
                        ('dinner', 'Dinner'),
                        ('post_workout', 'Post-workout'),
                        ('bedtime_snack', 'Bedtime Snack'),
                    ],
                    max_length=30,
                )),
                ('day_number', models.PositiveIntegerField(help_text='Day of the plan (1, 2, 3...)')),
                ('scheduled_time', models.TimeField(blank=True, null=True)),
                ('title', models.CharField(max_length=255)),
                ('foods_json', models.JSONField(blank=True, default=list)),
                ('calories', models.IntegerField(default=0)),
                ('protein', models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ('carbs', models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ('fat', models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ('portion_notes', models.CharField(blank=True, max_length=255)),
                ('substitutions', models.JSONField(blank=True, default=list)),
                ('sort_order', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('meal_plan', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='entries',
                    to='dashboard.mealplan',
                )),
                ('actual_meal', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='planned_entries',
                    to='dashboard.usermeal',
                )),
            ],
            options={
                'verbose_name': 'Meal Entry',
                'verbose_name_plural': 'Meal Entries',
                'ordering': ['day_number', 'sort_order'],
                'indexes': [
                    models.Index(fields=['meal_plan', 'day_number'], name='dashboard_me_plan_day_idx'),
                ],
            },
        ),

        # --- Phase 4: Rename old columns so the data migration can read them ---
        migrations.RenameField(model_name='mealplan', old_name='meal_type', new_name='_old_meal_type'),
        migrations.RenameField(model_name='mealplan', old_name='meal_name', new_name='_old_meal_name'),
        migrations.RenameField(model_name='mealplan', old_name='foods_json', new_name='_old_foods_json'),
        migrations.RenameField(model_name='mealplan', old_name='total_calories', new_name='_old_total_calories'),
        migrations.RenameField(model_name='mealplan', old_name='total_protein', new_name='_old_total_protein'),
        migrations.RenameField(model_name='mealplan', old_name='total_carbs', new_name='_old_total_carbs'),
        migrations.RenameField(model_name='mealplan', old_name='total_fat', new_name='_old_total_fat'),

        # --- Phase 5: Move existing data into MealEntry rows ---
        migrations.RunPython(migrate_existing_mealplans, migrations.RunPython.noop),

        # --- Phase 6: Drop old columns ---
        migrations.RemoveField(model_name='mealplan', name='_old_meal_type'),
        migrations.RemoveField(model_name='mealplan', name='_old_meal_name'),
        migrations.RemoveField(model_name='mealplan', name='_old_foods_json'),
        migrations.RemoveField(model_name='mealplan', name='_old_total_calories'),
        migrations.RemoveField(model_name='mealplan', name='_old_total_protein'),
        migrations.RemoveField(model_name='mealplan', name='_old_total_carbs'),
        migrations.RemoveField(model_name='mealplan', name='_old_total_fat'),

        # --- Phase 7: Expand UserMeal meal_type choices to match ---
        migrations.AlterField(
            model_name='usermeal',
            name='meal_type',
            field=models.CharField(
                choices=[
                    ('breakfast', 'Breakfast'),
                    ('mid_morning_snack', 'Mid-morning Snack'),
                    ('lunch', 'Lunch'),
                    ('evening_snack', 'Evening Snack'),
                    ('dinner', 'Dinner'),
                    ('post_workout', 'Post-workout'),
                    ('bedtime_snack', 'Bedtime Snack'),
                ],
                max_length=30,
            ),
        ),
    ]
