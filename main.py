import sqlite3
import xml.etree.ElementTree as et
from contextlib import closing  # автоматическое закрытие соединения с БД
from pathlib import Path

# создание приложения, получение данных из форм, отправка ошибок, объект входящего запроса, для передачи запроса в пост
from fastapi import FastAPI, Form, HTTPException, Request, Body
# ответ в виде HTML-страницы, XML ответ, перенаправление на другую страницу
from fastapi.responses import HTMLResponse, Response, RedirectResponse
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "clinic.db"
app = FastAPI(
    title="Медицинская клиника API",
    description="Приложение для 4 лабораторной"
)
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # преобразовывает результаты из кортежей в словарь
    conn.execute("PRAGMA foreign_keys = ON")  # проверка внешних ключей на существование
    return conn


def init_db():
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            birth_date TEXT NOT NULL,
            phone TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            specialization TEXT NOT NULL,
            phone TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_date TEXT NOT NULL,
            diagnosis TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE RESTRICT,
            FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE RESTRICT
        );
        """)

        # заполнение тестовыми данными, только при первом создании таблиц
        if cursor.execute("SELECT COUNT(*) FROM patients").fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO patients (full_name, birth_date, phone) VALUES (?, ?, ?)",
                [
                    ("Иванов Иван Иванович", "1985-04-12", "+7-900-111-22-33"),
                    ("Петрова Анна Сергеевна", "1992-09-25", "+7-900-222-33-44"),
                    ("Сидоров Максим Олегович", "1978-01-08", "+7-900-333-44-55"),
                ],
            )
        if cursor.execute("SELECT COUNT(*) FROM doctors").fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO doctors (full_name, specialization, phone) VALUES (?, ?, ?)",
                [
                    ("Смирнова Елена Викторовна", "Терапевт", "+7-900-444-55-66"),
                    ("Кузнецов Андрей Павлович", "Кардиолог", "+7-900-555-66-77"),
                ],
            )
        if cursor.execute("SELECT COUNT(*) FROM appointments").fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO appointments (patient_id, doctor_id, appointment_date, diagnosis) VALUES (?, ?, ?, ?)",
                [
                    (1, 1, "2026-10-20 10:00", "ОРВИ"),
                    (2, 2, "2026-10-21 12:30", ""),
                    (3, 1, "2026-10-22 09:15", "Повышенное давление"),
                ],
            )
        conn.commit()


@app.on_event("startup")  # при запуске сервера
def startup():
    init_db()


@app.get("/", response_class=HTMLResponse)  # главная страница
def home(request: Request):
    with closing(get_connection()) as conn:
        patients = conn.execute("SELECT * FROM patients ORDER BY id").fetchall()

        doctors = conn.execute("SELECT * FROM doctors ORDER BY id").fetchall()

        appointments = conn.execute("""
            SELECT a.id,
                   p.full_name AS patient_name,
                   d.full_name AS doctor_name,
                   d.specialization,
                   a.appointment_date,
                   a.diagnosis
            FROM appointments a
            JOIN patients p ON p.id = a.patient_id
            JOIN doctors d ON d.id = a.doctor_id
            ORDER BY a.id
        """).fetchall()

    # передача данных в HTML
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "patients": patients,
            "doctors": doctors,
            "appointments": appointments,
        }
    )


@app.post("/form/patients")
def create_patient_form(full_name: str = Form(...), birth_date: str = Form(...), phone: str = Form(...)):
    with closing(get_connection()) as conn:
        conn.execute("INSERT INTO patients (full_name, birth_date, phone) VALUES (?, ?, ?)",
                     (full_name, birth_date, phone))
        conn.commit()
    return RedirectResponse("/", status_code=303) # на главную после выполнения


@app.post("/form/doctors")
def create_doctor_form(full_name: str = Form(...), specialization: str = Form(...), phone: str = Form("")):
    with closing(get_connection()) as conn:
        conn.execute("INSERT INTO doctors (full_name, specialization, phone) VALUES (?, ?, ?)",
                     (full_name, specialization, phone))
        conn.commit()
    return RedirectResponse("/", status_code=303) # на главную после выполнения


@app.post("/form/appointments")
def create_appointment_form(patient_id: int = Form(...), doctor_id: int = Form(...),
                            appointment_date: str = Form(...), diagnosis: str = Form("")):
    try:
        with closing(get_connection()) as conn:
            conn.execute("""INSERT INTO appointments
                (patient_id, doctor_id, appointment_date, diagnosis) VALUES (?, ?, ?, ?)""",
                         (patient_id, doctor_id, appointment_date, diagnosis))
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Указанный пациент или врач не существует")
    return RedirectResponse("/", status_code=303) # на главную после выполнения


@app.get("/api/patients")
def get_patients():
    with closing(get_connection()) as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM patients ORDER BY id").fetchall()]


@app.get("/api/doctors")
def get_doctors():
    with closing(get_connection()) as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM doctors ORDER BY id").fetchall()]


@app.get("/api/appointments")
def get_appointments():
    with closing(get_connection()) as conn:
        rows = conn.execute("""SELECT a.*, p.full_name AS patient_name,
            d.full_name AS doctor_name FROM appointments a
            JOIN patients p ON p.id=a.patient_id JOIN doctors d ON d.id=a.doctor_id
            ORDER BY a.id""").fetchall()
        return [dict(row) for row in rows]


@app.post("/api/patients", status_code=201)
def add_patient(data: dict):
    required = ("full_name", "birth_date", "phone")
    if any(not data.get(field) for field in required): # не все обязательные поля переданы
        raise HTTPException(status_code=400, detail="Нужны full_name, birth_date и phone")
    with closing(get_connection()) as conn:
        cursor = conn.execute("INSERT INTO patients (full_name, birth_date, phone) VALUES (?, ?, ?)",
                              tuple(data[field] for field in required))
        conn.commit()
        return {"id": cursor.lastrowid, **data}


@app.post("/api/doctors", status_code=201)
def add_doctor(data: dict):
    required = ("full_name", "specialization", "phone")
    if any(not data.get(field) for field in required): # не все обязательные поля переданы
        raise HTTPException(status_code=400, detail="Нужны full_name, specialization и phone")
    with closing(get_connection()) as conn:
        cursor = conn.execute("INSERT INTO doctors (full_name, specialization, phone) VALUES (?, ?, ?)",
                              tuple(data[field] for field in required))
        conn.commit()
        return {"id": cursor.lastrowid, **data}


@app.post("/api/appointments", status_code=201)
def add_appointment(data: dict):
    required = ("patient_id", "doctor_id", "appointment_date")
    if any(field not in data for field in required): # не все обязательные поля переданы
        raise HTTPException(status_code=400, detail="Нужны patient_id, doctor_id и appointment_date")
    try:
        with closing(get_connection()) as conn:
            cursor = conn.execute("""INSERT INTO appointments
                (patient_id, doctor_id, appointment_date, diagnosis) VALUES (?, ?, ?, ?)""",
                                  (data["patient_id"], data["doctor_id"], data["appointment_date"],
                                   data.get("diagnosis", "")))
            conn.commit()
            return {"id": cursor.lastrowid, **data}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Пациент или врач с таким id не найден")


# экспорт и импорт таблицы patients из SQLite в XML
@app.get("/xml/export/patients")
def export_patients_xml():
    root = et.Element("patients") # корневой элемент
    with closing(get_connection()) as conn:
        rows = conn.execute("SELECT * FROM patients ORDER BY id").fetchall()
    for row in rows:
        patient = et.SubElement(root, "patient") # дочерний элемент
        for key in ("id", "full_name", "birth_date", "phone"):
            et.SubElement(patient, key).text = str(row[key])
    xml_data = et.tostring(root, encoding="utf-8", xml_declaration=True)
    return Response(content=xml_data, media_type="application/xml",
                    headers={"Content-Disposition": "attachment; filename=patients.xml"})


@app.post("/xml/import/patients")
async def import_patients_xml(xml_data: str = Body(..., media_type="application/xml")): # асинхронное чтение запроса
    return await _import_patients_xml(xml_data.encode("utf-8"))


async def _import_patients_xml(raw: bytes):
    try:
        root = et.fromstring(raw)
        if root.tag != "patients":
            raise ValueError("Корневой элемент должен называться patients")
        records = []
        for item in root.findall("patient"):
            records.append((
                 int(item.findtext("id")),
                 item.findtext("full_name"),
                 item.findtext("birth_date"),
                 item.findtext("phone")
            ))
        if any(not full_name or not birth_date or not phone for _, full_name, birth_date, phone in records):
            raise ValueError("В каждой записи должны быть full_name, birth_date и phone")
        with closing(get_connection()) as conn:
            conn.executemany("""INSERT INTO patients (id, full_name, birth_date, phone)
                VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET
                full_name=excluded.full_name, birth_date=excluded.birth_date, phone=excluded.phone""", records)
            conn.commit()
        return {"message": "Импорт завершён", "imported": len(records)}
    except (et.ParseError, ValueError, TypeError, sqlite3.IntegrityError) as exc:
        raise HTTPException(status_code=400, detail=f"Ошибка XML-импорта: {exc}")
