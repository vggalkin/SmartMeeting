# apps/bookings/services.py
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Booking


class BookingService:

    @staticmethod
    def is_room_available(room_id, start_time, end_time, exclude_booking_id=None):
        """Проверка доступности комнаты"""
        overlapping = Booking.objects.filter(
            room_id=room_id,
            status__in=['confirmed', 'pending'],
            start_time__lt=end_time,
            end_time__gt=start_time
        )

        if exclude_booking_id:
            overlapping = overlapping.exclude(id=exclude_booking_id)

        return not overlapping.exists()

    @staticmethod
    def get_available_slots(room_id, date):
        """Получить свободные слоты на день (30-минутные интервалы)"""
        from datetime import datetime, timedelta

        start_of_day = datetime.combine(date, datetime.min.time())
        end_of_day = datetime.combine(date, datetime.max.time())

        booked = Booking.objects.filter(
            room_id=room_id,
            status__in=['confirmed', 'pending'],
            start_time__lt=end_of_day,
            end_time__gt=start_of_day
        ).values_list('start_time', 'end_time')

        # Генерируем все 30-минутные слоты с 8:00 до 22:00
        slots = []
        current = datetime.combine(date, datetime.strptime('08:00', '%H:%M').time())
        end = datetime.combine(date, datetime.strptime('22:00', '%H:%M').time())

        while current < end:
            slot_end = current + timedelta(minutes=30)

            # Проверяем, не занят ли слот
            is_free = True
            for booked_start, booked_end in booked:
                if not (slot_end <= booked_start or current >= booked_end):
                    is_free = False
                    break

            if is_free:
                slots.append({
                    'start': current,
                    'end': slot_end,
                    'start_str': current.strftime('%H:%M'),
                    'end_str': slot_end.strftime('%H:%M')
                })

            current = slot_end

        return slots
