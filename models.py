from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class PasswordMixin:
    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


class User(db.Model, PasswordMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), default='')
    bio = db.Column(db.Text, default='')
    role = db.Column(db.String(20), nullable=False)  # 'admin' or 'verifier'
    title = db.Column(db.String(120), default='')  # admin only
    organization = db.Column(db.String(120), default='')  # verifier only
    password_hash = db.Column(db.String(255), nullable=False)
    profile_picture = db.Column(db.String(120), nullable=True)

    @property
    def initials(self):
        parts = self.name.split()
        return ''.join(p[0] for p in parts[:2]).upper()


class Student(db.Model, PasswordMixin):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    program = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'Enrolled' or 'Not Enrolled'
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), default='')
    phone = db.Column(db.String(30), default='')
    bio = db.Column(db.Text, default='')
    profile_picture = db.Column(db.String(120), nullable=True)
    faculty = db.Column(db.String(150), default='')
    graduation_year = db.Column(db.String(10), default='')

    @property
    def initials(self):
        parts = self.name.split()
        return ''.join(p[0] for p in parts[:2]).upper()

    previous_schools = db.relationship(
        'PreviousSchool', backref='student', cascade='all, delete-orphan'
    )
    certificates = db.relationship(
        'Certificate', backref='student_fk', cascade='all, delete-orphan'
    )


class PreviousSchool(db.Model):
    __tablename__ = 'previous_schools'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    school = db.Column(db.String(150), nullable=False)
    certificate = db.Column(db.String(150), nullable=False)
    year = db.Column(db.String(10), nullable=False)


class Certificate(db.Model):
    __tablename__ = 'certificates'

    # templates read this as `cert.id`, so the business key (e.g. "CERT-8821")
    # IS the primary key rather than living in a separate column.
    id = db.Column(db.String(20), primary_key=True)
    student_id_fk = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    course = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'Active' or 'Revoked'
    comments = db.Column(db.Text, default='')
    issued_date = db.Column(db.String(20), default='')
    revoked_date = db.Column(db.String(20), default='')
    classification = db.Column(db.String(120), default='')
    file_path = db.Column(db.String(120), nullable=True)
    file_hash = db.Column(db.String(64), nullable=True)
    source = db.Column(db.String(10), default='admin')  # 'admin' or 'student'
    issuing_institution = db.Column(db.String(150), default='')
    issued_by_admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    @property
    def student(self):
        return self.student_fk.name

    @property
    def student_id(self):
        return self.student_fk.student_id


class VerificationRecord(db.Model):
    __tablename__ = 'verification_records'

    # templates read this as `record.id` (e.g. "VER-3001")
    id = db.Column(db.String(20), primary_key=True)
    cert_id = db.Column(db.String(20), nullable=False)  # loose reference, not a FK
    student = db.Column(db.String(120), nullable=False)
    qualification = db.Column(db.String(150), nullable=False)
    institution = db.Column(db.String(150), nullable=False)
    date = db.Column(db.String(30), nullable=False)
    result = db.Column(db.String(20), nullable=False)  # 'Verified' or 'Failed'
    reason = db.Column(db.Text, default='')


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    recipient_role = db.Column(db.String(10), nullable=False)  # 'admin', 'student', or 'verifier'
    recipient_id = db.Column(db.Integer, nullable=True)  # User.id or Student.id depending on recipient_role
    record_id = db.Column(db.String(20), nullable=True)  # the VerificationRecord this is about
    cert_id = db.Column(db.String(20), nullable=True)  # denormalized from the record, for easy linking
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.String(40), nullable=False)
