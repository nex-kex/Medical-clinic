# Медицинская клиника

Учебное веб-приложение для управления медицинской клиникой на Python, FastAPI и SQLite с REST API, HTML-формами и импортом/экспортом XML.

## 1. Установка и запуск

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

- HTML-интерфейс: http://127.0.0.1:8000. 
- Документация API: http://127.0.0.1:8000/docs.

При первом запуске автоматически создаётся файл `clinic.db`, три связанные таблицы и демонстрационные записи.

## 2. Структура БД

1. `patients`: пациенты (первичный ключ `id`).

| Поле | Тип | Назначение                |
|---|---|---------------------------|
| id | integer | Уникальный номер пациента |
| full_name | text | ФИО                       |
| birth_date | text | Дата рождения             |
| phone | text | Телефон                   |

2. `doctors`: врачи (первичный ключ `id`).

| Поле           | Тип | Назначение             |
|----------------|---|------------------------|
| id             | integer | Уникальный номер врача |
| full_name      | text | ФИО                    |
| specialization | text | Специализация          |
| phone          | text | Телефон                |

3. `appointments`: приёмы; `patient_id` ссылается на `patients.id`, `doctor_id` — на `doctors.id`.

| Поле             | Тип | Назначение              |
|------------------|---|-------------------------|
| id               | integer | Уникальный номер приёма |
| patient_id       | integer | ID пациента             |
| doctor_id        | integer | ID врача                |
| appointment_date | text | Дата и время приёма     |
| diagnosis        | text | Диагноз                 |

## 3. requirements

```bash
pip install fastapi uvicorn jinja2 python-multipart
pip freeze > requirements.txt
```

- `fastapi` — библиотека для создания веб-приложений и API;
- `uvicorn` — сервер, который запускает приложение FastAPI;
- `jinja2` — шаблонизатор для создания HTML-страниц с динамическими данными;
- `python-multipart` — необходим для обработки HTML-форм с отправкой данных методом POST.

## 4. API

| Метод | URL | Назначение |
|---|---|---|
| GET | `/api/patients` | Получить пациентов |
| POST | `/api/patients` | Добавить пациента |
| GET | `/api/doctors` | Получить врачей |
| POST | `/api/doctors` | Добавить врача |
| GET | `/api/appointments` | Получить приёмы |
| POST | `/api/appointments` | Добавить приём |
| GET | `/xml/export/patients` | Скачать пациентов как XML |
| POST | `/xml/import/patients` | Импортировать пациентов из XML в теле запроса |

## 5. XML-импорт

Сначала скачайте XML по адресу `/xml/export/patients`. 
Для обратного импорта отправьте содержимое XML в POST `/xml/import/patients`, заголовок `Content-Type: application/xml`. Импорт использует ID из XML: новая запись добавляется, существующая с тем же ID обновляется.
