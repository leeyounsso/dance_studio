from datetime import datetime, timedelta, timezone

from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-me-to-a-random-secret-for-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///studio.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    teacher = db.relationship('Teacher', uselist=False, back_populates='user')
    student = db.relationship('Student', uselist=False, back_populates='user')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Direction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    photo = db.Column(db.String(200), nullable=True)
    groups = db.relationship('Group', back_populates='direction')


class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bio = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', back_populates='teacher')
    groups = db.relationship('Group', back_populates='teacher')
    stage_name = db.Column(db.String(100), nullable=True)


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', back_populates='student')
    tablename = 'student'
    bookings = db.relationship('Booking', back_populates='student', cascade='all, delete-orphan')
    payments = db.relationship('Payment', back_populates='student')
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)
    group = db.relationship('Group', back_populates='students')


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    direction_id = db.Column(db.Integer, db.ForeignKey('direction.id'))
    direction = db.relationship('Direction', back_populates='groups')
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'))
    teacher = db.relationship('Teacher', back_populates='groups')
    capacity = db.Column(db.Integer, nullable=False, default=12)
    location = db.Column(db.String(200), nullable=True)
    lessons = db.relationship('Lesson', back_populates='group')
    students = db.relationship('Student', back_populates='group')


class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    group = db.relationship('Group', back_populates='lessons')
    start_dt = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=60)
    bookings = db.relationship('Booking', back_populates='lesson')


class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False, default=0.0)
    sessions = db.Column(db.Integer, nullable=False, default=1)


class Abonement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    direction_id = db.Column(db.Integer, db.ForeignKey('direction.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    attended = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    tablename = 'booking'
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    lesson = db.relationship('Lesson', back_populates='bookings')

    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    student = db.relationship('Student', back_populates='bookings')


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    student = db.relationship('Student', back_populates='payments')
    amount = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


def current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    return User.query.get(uid)

def login_user(user):
    session['user_id'] = user.id

def logout_user():
    session.pop('user_id', None)

def require_role(*roles):
    user = current_user()
    if not user or user.role not in roles:
        abort(403)

@app.route('/')
def index():
    directions = Direction.query.all()
    teachers = Teacher.query.all()
    upcoming = Lesson.query.filter(Lesson.start_dt >= datetime.now(timezone.utc)).order_by(Lesson.start_dt).limit(12).all()
    return render_template('index.html', directions=directions, teachers=teachers, upcoming=upcoming, user=current_user())

@app.route('/subscriptions')
def subscriptions():
    return render_template('subscriptions.html', user=current_user())
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        pw = request.form['password']
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(pw):
            flash('Неверный email или пароль', 'danger')
            return redirect(url_for('login'))
        login_user(user)
        flash('Вход выполнен', 'success')
        return redirect(url_for('index'))
    return render_template('login.html', user=current_user())

from werkzeug.security import generate_password_hash
from flask import request, flash, redirect, url_for, render_template

@app.route('/register', methods=['GET', 'POST'])
def register():
    u = current_user()
    if u:
        flash("Вы уже авторизованы.", "info")
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '').strip()

        if not name or not email or not password:
            flash("Пожалуйста, заполните имя, email и пароль.", "warning")
            return render_template('register.html')

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Пользователь с таким email уже существует. Попробуйте войти или используйте другой email.", "warning")
            return render_template('register.html')

        user = User(
            name=name,
            email=email,
            role='student',
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.flush()
        student = Student(user_id=user.id, phone=phone)
        db.session.add(student)
        db.session.commit()

        flash("Регистрация прошла успешно. Войдите, пожалуйста.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    logout_user()
    flash('Вы вышли', 'info')
    return redirect(url_for('index'))

@app.route('/teachers')
def teachers():
    ts = Teacher.query.all()
    return render_template('teachers.html', teachers=ts, user=current_user())

@app.route('/teacher/<int:tid>')
def teacher_detail(tid):
    t = Teacher.query.get_or_404(tid)
    return render_template('teacher_detail.html', teacher=t, user=current_user())

@app.route('/directions')
def directions():
    ds = Direction.query.all()
    return render_template('directions.html', directions=ds, user=current_user())

@app.route('/groups')
def groups():
    gs = Group.query.all()
    return render_template('groups.html', groups=gs, user=current_user())

@app.route('/lessons')
def lessons():
    lessons = Lesson.query.order_by(Lesson.start_dt).all()
    return render_template('lessons.html', lessons=lessons, user=current_user())

@app.route('/lesson/<int:lid>')
def lesson_detail(lid):
    lesson = Lesson.query.get_or_404(lid)
    taken = Booking.query.filter_by(lesson_id=lesson.id).count()
    capacity = lesson.group.capacity
    spots_left = capacity - taken
    return render_template('lesson_detail.html', lesson=lesson, spots_left=spots_left, taken=taken, user=current_user())

@app.route('/book/<int:lid>', methods=['POST'])
def book_lesson(lid):
    user = current_user()
    if not user or getattr(user, "role", None) != 'student':
        flash("Только зарегистрированные студенты могут записываться.", "warning")
        return redirect(url_for('lesson_detail', lid=lid))

    lesson = Lesson.query.get(lid)
    if not lesson:
        flash("Урок не найден.", "danger")
        return redirect(url_for('lessons'))

    student = Student.query.filter_by(user_id=user.id).first()
    if not student:
        flash("Студентская запись не найдена — обратитесь к администратору.", "danger")
        return redirect(url_for('lessons'))

    taken = Booking.query.filter_by(lesson_id=lesson.id).count()
    spots_left = (lesson.group.capacity or 0) - taken
    if spots_left <= 0:
        flash("К сожалению, мест на этот урок нет.", "warning")
        return redirect(url_for('lesson_detail', lid=lid))

    already = Booking.query.filter_by(lesson_id=lesson.id, student_id=student.id).first()
    if already:
        flash("Вы уже записаны на этот урок.", "info")
        return redirect(url_for('lesson_detail', lid=lid))

    try:
        booking = Booking(
            student_name = user.name or student.user.name or "Студент",
            direction_id = lesson.group.direction_id if lesson.group else None,
            teacher_id = lesson.group.teacher_id if lesson.group else None,
            lesson_id = lesson.id,
            student_id = student.id,
            attended = False
        )
        db.session.add(booking)
        db.session.commit()
        flash("Вы успешно записаны на урок.", "success")
    except IntegrityError as e:
        db.session.rollback()
        flash("Ошибка записи — проверьте данные или свяжитесь с администратором.", "danger")

    return redirect(url_for('lesson_detail', lid=lid))

@app.route('/booking/<int:bid>/cancel', methods=['POST'])
def cancel_booking(bid):
    user = current_user()
    if not user or user.role != 'student':
        abort(403)
    b = Booking.query.get_or_404(bid)
    if b.student.user_id != user.id:
        abort(403)
    if b.lesson.start_dt < datetime.now(datetime.UTC):
        flash('Нельзя отменить прошедшее занятие', 'warning')
        return redirect(url_for('student_profile'))
    db.session.delete(b)
    db.session.commit()
    flash('Запись отменена', 'info')
    return redirect(url_for('student_profile'))

@app.route('/me')
def student_profile():
    user = current_user()
    if not user:
        abort(403)
    if user.role == 'student':
        bookings = Booking.query.join(Lesson).filter(Booking.student_id==user.student.id).order_by(Lesson.start_dt).all()
        payments = Payment.query.filter_by(student_id=user.student.id).order_by(Payment.created_at.desc()).all()
        return render_template('student_profile.html', bookings=bookings, payments=payments, user=user)
    elif user.role == 'teacher':
        t = user.teacher
        lessons = Lesson.query.join(Group).filter(Group.teacher_id==t.id).order_by(Lesson.start_dt).all()
        return render_template('teacher_detail.html', teacher=t, lessons=lessons, user=user)
    elif user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        abort(403)

@app.route('/admin')
def admin_dashboard():
    require_role('admin')
    stats = {
        'students': Student.query.count(),
        'teachers': Teacher.query.count(),
        'directions': Direction.query.count(),
        'upcoming_lessons': Lesson.query.filter(Lesson.start_dt >= datetime.now(timezone.utc)).count()
    }
    return render_template('admin_dashboard.html', stats=stats, user=current_user())

@app.route('/admin/add_direction', methods=['GET','POST'])
def admin_add_direction():
    require_role('admin')
    if request.method == 'POST':
        name = request.form['name'].strip()
        desc = request.form.get('description','').strip()
        if not name:
            flash('Название обязательно', 'danger')
            return redirect(url_for('admin_add_direction'))
        db.session.add(Direction(name=name, description=desc))
        db.session.commit()
        flash('Направление добавлено', 'success')
        return redirect(url_for('directions'))
    return render_template('direction_form.html', user=current_user())

@app.route('/admin/add_group', methods=['GET','POST'])
def admin_add_group():
    require_role('admin')
    directions = Direction.query.all()
    teachers = Teacher.query.all()
    if request.method == 'POST':
        name = request.form['name'].strip()
        direction_id = int(request.form['direction_id'])
        teacher_id = int(request.form['teacher_id'])
        capacity = int(request.form['capacity'])
        location = request.form.get('location','').strip()
        if capacity <= 0:
            flash('Количество мест должно быть > 0', 'danger')
            return redirect(url_for('admin_add_group'))
        g = Group(name=name, direction_id=direction_id, teacher_id=teacher_id, capacity=capacity, location=location)
        db.session.add(g); db.session.commit()
        flash('Группа создана', 'success')
        return redirect(url_for('groups'))
    return render_template('group_form.html', directions=directions, teachers=teachers, user=current_user())

@app.route('/admin/add_lesson', methods=['GET','POST'])
def admin_add_lesson():
    require_role('admin')
    groups = Group.query.all()
    if request.method == 'POST':
        group_id = int(request.form['group_id'])
        dt_str = request.form['start_dt'].strip()
        duration = int(request.form.get('duration', '60'))
        try:
            start_dt = datetime.fromisoformat(dt_str)
        except Exception:
            flash('Неверный формат даты/времени', 'danger')
            return redirect(url_for('admin_add_lesson'))
        if start_dt < datetime.now() - timedelta(minutes=30):
            flash('Нельзя создавать урок в прошлом', 'danger')
            return redirect(url_for('admin_add_lesson'))
        lesson = Lesson(group_id=group_id, start_dt=start_dt, duration_minutes=duration)
        db.session.add(lesson); db.session.commit()
        flash('Урок добавлен', 'success')
        return redirect(url_for('lessons'))
    return render_template('lesson_form.html', groups=groups, user=current_user())

@app.route('/admin/add_student', methods=['GET', 'POST'])
def admin_add_student():

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        group_id = request.form.get('group_id')

        user = User(
            name=name,
            email=email,
            role='student',
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.flush()
        student = Student(user_id=user.id, group_id=group_id)
        db.session.add(student)
        db.session.commit()

        flash('Студент успешно добавлен!', 'success')
        return redirect(url_for('admin_dashboard'))

    groups = Group.query.all()
    return render_template('add_student.html', groups=groups)

@app.route('/abonements')
def abonements():
    abonements = Abonement.query.all()
    return render_template('abonements.html', abonements=abonements, user=current_user())

@app.route('/admin/add_abonement', methods=['GET', 'POST'])
def admin_add_abonement():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        a = Abonement(name=name, description=description, price=price)
        db.session.add(a)
        db.session.commit()
        flash('Абонемент добавлен!', 'success')
        return redirect(url_for('abonements'))
    return render_template('admin_add_abonement.html', user=current_user())

@app.route('/admin/edit_abonement/<int:aid>', methods=['GET', 'POST'])
def admin_edit_abonement(aid):
    a = Abonement.query.get_or_404(aid)
    if request.method == 'POST':
        a.name = request.form['name']
        a.description = request.form['description']
        a.price = float(request.form['price'])
        db.session.commit()
        flash('Абонемент обновлён!', 'success')
        return redirect(url_for('abonements'))
    return render_template('admin_edit_abonement.html', abonement=a, user=current_user())

@app.route('/admin/attendance/<int:lesson_id>', methods=['GET','POST'])
def mark_attendance(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    user = current_user()
    if not user:
        abort(403)
    if user.role == 'teacher':
        if lesson.group.teacher.user_id != user.id:
            abort(403)
    elif user.role != 'admin':
        abort(403)
    bookings = Booking.query.filter_by(lesson_id=lesson.id).all()
    if request.method == 'POST':
        present_ids = request.form.getlist('present')
        for b in bookings:
            b.attended = str(b.id) in present_ids
        db.session.commit()
        flash('Посещаемость сохранена', 'success')
        return redirect(url_for('lesson_detail', lid=lesson.id))
    return render_template('admin_students.html', lesson=lesson, bookings=bookings, user=user)

@app.route('/admin/students')
def admin_students():
    user = current_user()
    if not user or user.role != 'admin':
        return redirect(url_for('login'))

    students = Student.query.all()
    return render_template('admin_students.html', students=students, user=user)

@app.route('/admin/mark_attendance/<int:booking_id>', methods=['POST'])
def admin_mark_attendance(booking_id):
    user = current_user()
    if not user or user.role != 'admin':
        return redirect(url_for('login'))

    booking = Booking.query.get_or_404(booking_id)
    booking.attended = not booking.attended
    db.session.commit()
    return redirect(url_for('admin_students'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)