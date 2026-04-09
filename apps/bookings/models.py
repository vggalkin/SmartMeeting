# apps/bookings/models.py
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.rooms.models import Room


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('confirmed', 'Подтверждено'),
        ('cancelled', 'Отменено'),
        ('completed', 'Завершено'),
        ('rejected', 'Отклонено'),
    ]

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='bookings', verbose_name='Переговорная')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings',
                             verbose_name='Пользователь')

    title = models.CharField('Название встречи', max_length=200)
    description = models.TextField('Описание', blank=True)

    start_time = models.DateTimeField('Начало')
    end_time = models.DateTimeField('Конец')

    attendees_count = models.PositiveIntegerField('Количество участников', default=1)

    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='confirmed')

    needs_projector = models.BooleanField('Нужен проектор', default=False)
    needs_video_conf = models.BooleanField('Нужна видеоконференция', default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reminder_sent = models.BooleanField('Напоминание отправлено', default=False)

    class Meta:
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.room.name} - {self.start_time.strftime('%d.%m %H:%M')} - {self.user.username}"

    def clean(self):
        """Валидация на уровне модели"""
        # Проверяем, что поля не None
        if self.start_time is None or self.end_time is None:
            return  # Если поля не заполнены, не выполняем валидацию

        if self.start_time >= self.end_time:
            raise ValidationError('Время начала должно быть раньше времени окончания')

        if self.start_time < timezone.now():
            raise ValidationError('Нельзя бронировать прошедшее время')

        # Максимум 4 часа
        duration = (self.end_time - self.start_time).total_seconds() / 3600
        if duration > 4:
            raise ValidationError('Максимальная длительность бронирования - 4 часа')

        # Минимум 15 минут
        if duration < 0.25:
            raise ValidationError('Минимальная длительность бронирования - 15 минут')

    def save(self, *args, **kwargs):
        # Вызываем clean только если поля заполнены
        if self.start_time and self.end_time:
            self.full_clean()
        super().save(*args, **kwargs)
