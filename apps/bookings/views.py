# apps/bookings/views.py (полностью обновленная версия)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from datetime import datetime
from .models import Booking
from .forms import BookingForm
from .services import BookingService
from apps.rooms.models import Room
from apps.notifications.tasks import send_booking_reminder
from datetime import timedelta


def home_view(request):
    """Главная страница"""
    context = {
        'title': 'SmartMeeting - Система бронирования переговорных',
    }

    if request.user.is_authenticated:
        upcoming_bookings = Booking.objects.filter(
            user=request.user,
            start_time__gte=timezone.now(),
            status__in=['confirmed', 'pending']
        ).select_related('room').order_by('start_time')[:5]

        context['upcoming_bookings'] = upcoming_bookings
        context['rooms_count'] = Room.objects.filter(is_active=True).count()
        context['my_bookings_count'] = Booking.objects.filter(user=request.user).count()

    return render(request, 'home.html', context)


@login_required
def calendar_view(request):
    """Календарь бронирований"""
    rooms = Room.objects.filter(is_active=True)
    my_bookings = Booking.objects.filter(
        user=request.user,
        start_time__gte=timezone.now(),
        status__in=['confirmed', 'pending']
    ).select_related('room').order_by('start_time')[:10]

    context = {
        'rooms': rooms,
        'my_bookings': my_bookings,
    }
    return render(request, 'bookings/calendar.html', context)


@login_required
def create_booking(request):
    """Создание нового бронирования"""
    from django.utils.timezone import make_aware
    from datetime import datetime, timedelta

    # Обработка GET параметров для предзаполнения
    start_param = request.GET.get('start')
    initial_data = {}

    if start_param:
        try:
            # Парсим дату из запроса
            if 'T' in start_param:
                start_datetime = datetime.fromisoformat(start_param.replace('Z', '+00:00'))
                # Преобразуем в локальное время без часового пояса для формы
                start_datetime = start_datetime.replace(tzinfo=None)
                initial_data['start_time'] = start_datetime
        except:
            pass

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            try:
                # Получаем объединенные дату и время из cleaned_data
                start_datetime = form.cleaned_data.get('start_datetime')
                end_datetime = form.cleaned_data.get('end_datetime')

                if not start_datetime or not end_datetime:
                    messages.error(request, '❌ Ошибка: не указано время начала или окончания')
                    return render(request, 'bookings/booking_form.html',
                                  {'form': form, 'title': 'Создание бронирования'})

                # Создаем бронирование
                booking = Booking(
                    user=request.user,
                    room=form.cleaned_data['room'],
                    title=form.cleaned_data['title'],
                    description=form.cleaned_data.get('description', ''),
                    start_time=start_datetime,
                    end_time=end_datetime,
                    attendees_count=form.cleaned_data['attendees_count'],
                    needs_projector=form.cleaned_data['needs_projector'],
                    needs_video_conf=form.cleaned_data['needs_video_conf'],
                    status='confirmed'  # Сразу подтверждаем
                )

                booking.save()
                messages.success(request,
                                 f'✅ Переговорная "{booking.room.name}" успешно забронирована на {start_datetime.strftime("%d.%m.%Y %H:%M")}!')
                reminder_time = start_datetime - timedelta(hours=1)
                if reminder_time > timezone.now():
                    send_booking_reminder.apply_async(
                        args=[booking.id],
                        eta=reminder_time
                    )
                    messages.info(request, '🔔 Напоминание будет отправлено за час до встречи')
                return redirect('calendar')
            except Exception as e:
                messages.error(request, f'❌ Ошибка при создании бронирования: {str(e)}')
        else:
            # Выводим все ошибки формы
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'❌ {field}: {error}')
    else:
        form = BookingForm(initial=initial_data)

    return render(request, 'bookings/booking_form.html', {
        'form': form,
        'title': 'Создание бронирования'
    })


@login_required
def get_events_api(request):
    """API для получения событий календаря"""
    start = request.GET.get('start')
    end = request.GET.get('end')

    bookings = Booking.objects.filter(
        user=request.user,
        start_time__gte=start,
        end_time__lte=end,
        status__in=['confirmed', 'pending']
    ).select_related('room')

    events = []
    for booking in bookings:
        events.append({
            'id': booking.id,
            'title': f"{booking.title} - {booking.room.name}",
            'start': booking.start_time.isoformat(),
            'end': booking.end_time.isoformat(),
            'room': booking.room.name,
            'status': booking.status,
            'color': '#28a745' if booking.status == 'confirmed' else '#ffc107',
            'textColor': '#000000'
        })

    return JsonResponse(events, safe=False)
