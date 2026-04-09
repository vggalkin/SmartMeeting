# apps/bookings/forms.py
from django import forms
from django.utils import timezone
from django.utils.timezone import localtime
from .models import Booking
from apps.rooms.models import Room


class BookingForm(forms.ModelForm):
    # Создаем отдельные поля для даты и времени
    date = forms.DateField(
        label='Дата',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    start_time = forms.TimeField(
        label='Время начала',
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time',
            'step': '900'  # Шаг 15 минут
        })
    )

    end_time = forms.TimeField(
        label='Время окончания',
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time',
            'step': '900'  # Шаг 15 минут
        })
    )

    class Meta:
        model = Booking
        fields = ['room', 'title', 'description', 'attendees_count',
                  'needs_projector', 'needs_video_conf']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Планёрка по проекту'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Опишите цель встречи...'
            }),
            'attendees_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'value': 2
            }),
            'room': forms.Select(attrs={'class': 'form-control'}),
            'needs_projector': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'needs_video_conf': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Ограничиваем выбор только активными комнатами
        self.fields['room'].queryset = Room.objects.filter(is_active=True)
        self.fields['room'].empty_label = "Выберите переговорную"

        # Устанавливаем минимальную дату - сегодня
        today = timezone.now().date()
        self.fields['date'].widget.attrs['min'] = today.strftime('%Y-%m-%d')

        # Устанавливаем рабочие часы (9:00 - 21:00)
        self.fields['start_time'].widget.attrs['min'] = '09:00'
        self.fields['start_time'].widget.attrs['max'] = '20:00'
        self.fields['end_time'].widget.attrs['min'] = '09:15'
        self.fields['end_time'].widget.attrs['max'] = '21:00'

        # Если есть начальные данные из GET параметров
        if self.initial.get('start_time'):
            start_datetime = self.initial['start_time']
            if start_datetime:
                self.fields['date'].initial = start_datetime.date()
                self.fields['start_time'].initial = start_datetime.time()
                # По умолчанию ставим +1 час
                from datetime import timedelta
                end_datetime = start_datetime + timedelta(hours=1)
                self.fields['end_time'].initial = end_datetime.time()

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        room = cleaned_data.get('room')

        if date and start_time and end_time:
            from django.utils.timezone import make_aware
            from datetime import datetime

            # Объединяем дату и время
            start_datetime = make_aware(datetime.combine(date, start_time))
            end_datetime = make_aware(datetime.combine(date, end_time))

            # Сохраняем в cleaned_data для использования в view
            cleaned_data['start_datetime'] = start_datetime
            cleaned_data['end_datetime'] = end_datetime

            # Валидации
            if start_datetime >= end_datetime:
                raise forms.ValidationError('Время начала должно быть раньше времени окончания')

            if start_datetime < timezone.now():
                raise forms.ValidationError('Нельзя бронировать прошедшее время')

            # Проверка длительности (максимум 4 часа)
            duration = (end_datetime - start_datetime).total_seconds() / 3600
            if duration > 4:
                raise forms.ValidationError('Максимальная длительность бронирования - 4 часа')

            if duration < 0.25:
                raise forms.ValidationError('Минимальная длительность бронирования - 15 минут')

            # Проверка рабочего времени
            if start_time.hour < 9 or start_time.hour > 20:
                raise forms.ValidationError('Бронирование возможно только с 9:00 до 21:00')

            # Проверка свободных слотов
            if room and start_datetime and end_datetime:
                from .services import BookingService
                if not BookingService.is_room_available(room.id, start_datetime, end_datetime):
                    raise forms.ValidationError('Эта переговорная уже занята в выбранное время')

        return cleaned_data
