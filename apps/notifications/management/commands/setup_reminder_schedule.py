# apps/notifications/management/commands/setup_reminder_schedule.py
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json


class Command(BaseCommand):
    help = 'Настраивает периодическую задачу для проверки напоминаний'

    def handle(self, *args, **options):
        # Создаем расписание - каждые 15 минут
        schedule, created = CrontabSchedule.objects.get_or_create(
            minute='*/15',  # каждые 15 минут
            hour='*',  # каждый час
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )

        # Создаем периодическую задачу
        PeriodicTask.objects.update_or_create(
            name='Check and send booking reminders',
            defaults={
                'task': 'apps.notifications.tasks.check_and_send_immediate_reminders',
                'crontab': schedule,
                'enabled': True,
                'args': json.dumps([]),
                'kwargs': json.dumps({}),
            }
        )

        self.stdout.write(self.style.SUCCESS('✅ Периодическая задача для напоминаний настроена!'))
