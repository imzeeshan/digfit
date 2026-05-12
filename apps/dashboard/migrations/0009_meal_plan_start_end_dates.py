import datetime

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0008_intervention_model'),
    ]

    operations = [
        migrations.RenameField(
            model_name='mealplan',
            old_name='meal_date',
            new_name='start_date',
        ),
        migrations.AddField(
            model_name='mealplan',
            name='end_date',
            field=models.DateField(default=datetime.date.today),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name='mealplan',
            options={
                'ordering': ['-start_date', 'meal_type'],
                'verbose_name': 'Meal Plan',
                'verbose_name_plural': 'Meal Plans',
            },
        ),
        migrations.RemoveIndex(
            model_name='mealplan',
            name='dashboard_m_user_id_1887b5_idx',
        ),
        migrations.AddIndex(
            model_name='mealplan',
            index=models.Index(fields=['user', '-start_date'], name='dashboard_m_user_id_a1b2c3_idx'),
        ),
    ]
