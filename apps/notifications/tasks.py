# apps/notifications/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_booking_reminder(booking_id):
    """Отправка напоминания о бронировании за час до начала"""
    from apps.bookings.models import Booking

    try:
        booking = Booking.objects.select_related('user', 'room').get(id=booking_id)

        # Проверяем, что напоминание еще не отправлено и время не прошло
        if booking.reminder_sent:
            return f"Reminder already sent for booking {booking_id}"

        # Проверяем, что до начала встречи остался примерно час
        time_until = booking.start_time - timezone.now()
        if time_until > timedelta(hours=1, minutes=10) or time_until < timedelta(minutes=50):
            return f"Not the right time for reminder (time_until: {time_until})"

        # Формируем письмо
        subject = f'🔔 Напоминание: "{booking.title}" через час'

        message = f"""
Здравствуйте, {booking.user.get_full_name() or booking.user.username}!

Напоминаем, что у вас запланирована встреча:

📋 {booking.title}
🏢 Переговорная: {booking.room.name} ({booking.room.floor} этаж)
📅 Дата: {booking.start_time.strftime('%d.%m.%Y')}
🕐 Время: {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}
👥 Участников: {booking.attendees_count}

{f'📝 Описание: {booking.description}' if booking.description else ''}

{f'📽️ Дополнительно: {", ".join([
            "проектор" if booking.needs_projector else "",
            "видеоконференция" if booking.needs_video_conf else ""
        ]).strip(", ")}' if booking.needs_projector or booking.needs_video_conf else ''}

Пожалуйста, не опаздывайте!

С уважением,
Команда SmartMeeting
        """

        # Отправляем email
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@smartmeeting.com',
            recipient_list=[booking.user.email],
            fail_silently=False,
        )

        # Отмечаем, что напоминание отправлено
        booking.reminder_sent = True
        booking.save(update_fields=['reminder_sent'])

        logger.info(f"Reminder sent for booking {booking_id} to {booking.user.email}")
        return f"Reminder sent successfully for booking {booking_id}"

    except Exception as e:
        logger.error(f"Error sending reminder for booking {booking_id}: {str(e)}")
        return f"Error: {str(e)}"


@shared_task
def schedule_reminders_for_tomorrow():
    """Запланировать напоминания на завтрашние встречи"""
    from apps.bookings.models import Booking

    tomorrow = timezone.now() + timedelta(days=1)
    tomorrow_start = tomorrow.replace(hour=0, minute=0, second=0)
    tomorrow_end = tomorrow.replace(hour=23, minute=59, second=59)

    bookings = Booking.objects.filter(
        start_time__gte=tomorrow_start,
        start_time__lte=tomorrow_end,
        status='confirmed',
        reminder_sent=False
    )

    scheduled_count = 0
    for booking in bookings:
        # Планируем напоминание за час до начала
        reminder_time = booking.start_time - timedelta(hours=1)
        if reminder_time > timezone.now():
            send_booking_reminder.apply_async(
                args=[booking.id],
                eta=reminder_time
            )
            scheduled_count += 1

    return f"Scheduled {scheduled_count} reminders for tomorrow"


@shared_task
def check_and_send_immediate_reminders():
    """Проверка и отправка немедленных напоминаний (запускать каждые 15 минут)"""
    from apps.bookings.models import Booking

    now = timezone.now()
    one_hour_later = now + timedelta(hours=1)

    # Находим встречи, которые начнутся примерно через час
    bookings = Booking.objects.filter(
        start_time__gte=now + timedelta(minutes=50),
        start_time__lte=now + timedelta(hours=1, minutes=10),
        status='confirmed',
        reminder_sent=False
    )

    sent_count = 0
    for booking in bookings:
        send_booking_reminder.delay(booking.id)
        sent_count += 1

    return f"Sent {sent_count} immediate reminders"

