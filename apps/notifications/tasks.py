# apps/notifications/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime


@shared_task
def send_booking_reminder(booking_id):
    """Отправка напоминания о бронировании"""
    from apps.bookings.models import Booking

    try:
        booking = Booking.objects.select_related('user', 'room').get(id=booking_id)

        if not booking.reminder_sent and booking.start_time:
            # Email
            send_mail(
                subject=f'Напоминание: {booking.title}',
                message=f"""
                Здравствуйте, {booking.user.username}!

                Напоминаем, что у вас запланирована встреча:
                📍 {booking.room.name}
                🕐 {booking.start_time.strftime('%d.%m.%Y %H:%M')} - {booking.end_time.strftime('%H:%M')}
                📝 {booking.title}

                С уважением, SmartMeeting
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[booking.user.email],
                fail_silently=False,
            )

            # Отмечаем, что напоминание отправлено
            booking.reminder_sent = True
            booking.save(update_fields=['reminder_sent'])

            return f"Reminder sent for booking {booking_id}"
    except Exception as e:
        return f"Error sending reminder: {str(e)}"


@shared_task
def check_upcoming_bookings():
    """Проверка ближайших бронирований (запускать каждый час)"""
    from django.utils import timezone
    from datetime import timedelta

    soon = timezone.now() + timedelta(minutes=15)

    from apps.bookings.models import Booking
    upcoming = Booking.objects.filter(
        start_time__lte=soon,
        start_time__gt=timezone.now(),
        status='confirmed',
        reminder_sent=False
    )

    for booking in upcoming:
        send_booking_reminder.delay(booking.id)

    return f"Checked {upcoming.count()} upcoming bookings"
