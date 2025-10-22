from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # создаём администратора
    admin = User(
        email="admin@studio.local",
        name="Администратор",
        role="admin",
        password_hash=generate_password_hash("admin123")
    )
    db.session.add(admin)
    db.session.commit()
    print("✅ Администратор создан: admin@studio.local / admin123")