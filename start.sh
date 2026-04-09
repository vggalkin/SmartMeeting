# Создаем миграции
python manage.py makemigrations accounts
python manage.py makemigrations rooms
python manage.py makemigrations bookings
python manage.py makemigrations notifications

# Применяем миграции
python manage.py migrate

# Создаем суперпользователя
python manage.py createsuperuser

# Собираем статику
python manage.py collectstatic

# Создаем переговорки
python manage.py create_rooms

# Настройка периодической задачи для напоминаний
python manage.py setup_reminder_schedule
