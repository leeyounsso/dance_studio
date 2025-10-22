from app import app, db

with app.app_context():
    try:
        db.session.execute(db.text("ALTER TABLE student ADD COLUMN group_id INTEGER"))
        db.session.commit()
        print("✅ Колонка group_id успешно добавлена в таблицу student.")
    except Exception as e:
        print("⚠️ Не удалось добавить колонку (возможно, она уже существует):", e)