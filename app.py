import hashlib
import io
import os
import secrets
import string
import uuid
from datetime import date, datetime
from functools import wraps

import qrcode
import qrcode.image.svg
from flask import Flask, render_template, request, redirect, url_for, session, Response, abort, send_from_directory
from werkzeug.utils import secure_filename

from models import db, User, Student, PreviousSchool, Certificate, VerificationRecord, Notification, PasswordResetRequest
from blockchain import Block, add_certificate_block, verify_chain, verify_certificate

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
os.makedirs(app.instance_path, exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'academic_credentials.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8 MB, covers profile photos and certificate PDFs
db.init_app(app)
with app.app_context():
    db.create_all()  # only creates missing tables (e.g. password_reset_requests); existing data is untouched

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
CERTIFICATE_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'certificates')
ALLOWED_PHOTO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CERTIFICATE_UPLOAD_FOLDER, exist_ok=True)

DASHBOARD_ROUTES = {
    'admin': 'admin_dashboard',
    'student': 'student_dashboard',
    'verifier': 'verifier_dashboard',
}


def login_required(role):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if session.get('role') != role:
                return redirect(url_for('login'))
            return view_func(*args, **kwargs)
        return wrapped
    return decorator


def save_profile_photo(file, prefix, old_filename=None):
    """Validates and saves an uploaded profile photo, returning its new filename."""
    original_name = secure_filename(file.filename or '')
    ext = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else ''
    if ext not in ALLOWED_PHOTO_EXTENSIONS:
        return None, "Photo must be a PNG, JPG, GIF, or WEBP image."

    new_filename = f"{prefix}_{uuid.uuid4().hex[:8]}.{ext}"
    file.save(os.path.join(UPLOAD_FOLDER, new_filename))

    if old_filename:
        old_path = os.path.join(UPLOAD_FOLDER, old_filename)
        if os.path.exists(old_path):
            os.remove(old_path)

    return new_filename, None


def save_certificate_file(file, cert_id):
    """Validates a PDF upload, computes its SHA-256 hash, and saves it. Returns (filename, file_hash, error)."""
    original_name = secure_filename(file.filename or '')
    ext = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else ''
    if ext != 'pdf':
        return None, None, "Certificate file must be a PDF."

    file_hash = hashlib.sha256(file.read()).hexdigest()
    file.seek(0)

    filename = f"{cert_id}.pdf"
    file.save(os.path.join(CERTIFICATE_UPLOAD_FOLDER, filename))
    return filename, file_hash, None


def generate_temp_password(length=10):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def next_student_id():
    existing = [s.student_id for s in Student.query.all()]
    numbers = [int(sid.split('-')[1]) for sid in existing if '-' in sid and sid.split('-')[1].isdigit()]
    next_number = max(numbers, default=1041) + 1
    return f"STU-{next_number}"


def next_cert_id():
    existing = [c.id for c in Certificate.query.all()]
    numbers = [int(cid.split('-')[1]) for cid in existing if '-' in cid and cid.split('-')[1].isdigit()]
    next_number = max(numbers, default=8864) + 1
    return f"CERT-{next_number}"


def next_verification_id():
    existing = [r.id for r in VerificationRecord.query.all()]
    numbers = [int(rid.split('-')[1]) for rid in existing if '-' in rid and rid.split('-')[1].isdigit()]
    next_number = max(numbers, default=3000) + 1
    return f"VER-{next_number}"


def change_password(account, form):
    """Validates and applies a password change from a profile page's form. Returns (success_message, error_message)."""
    current = form.get('current_password', '')
    new = form.get('new_password', '')
    confirm = form.get('confirm_password', '')

    if not account.check_password(current):
        return None, "Current password is incorrect."
    if len(new) < 6:
        return None, "New password must be at least 6 characters."
    if new != confirm:
        return None, "New password and confirmation do not match."

    account.set_password(new)
    db.session.commit()
    return "Password updated successfully.", None


def attach_notification_links(notifications, role):
    """Sets a transient .link_url on each notification, pointing somewhere relevant for that role.
    None if the certificate no longer exists."""
    for note in notifications:
        note.link_url = None
        if not note.cert_id or not Certificate.query.get(note.cert_id):
            continue
        if role == 'admin':
            note.link_url = url_for('admin_certificate_detail', cert_id=note.cert_id)
        elif role == 'student':
            note.link_url = url_for('student_certificate_views', cert_id=note.cert_id)
        elif role == 'verifier':
            # Not verifier_history_detail: that page is scoped to the viewer's own
            # organization, and this notification may be about another org's lookup.
            note.link_url = url_for('verify_certificate_public', cert_id=note.cert_id)
    return notifications


@app.context_processor
def inject_current_user():
    """Makes the logged-in account, loaded fresh from the database, available to every template as current_user."""
    role = session.get('role')
    user_id = session.get('user_id')
    if not role or not user_id:
        return {'current_user': None}
    model = Student if role == 'student' else User
    return {'current_user': model.query.get(user_id)}


@app.route('/')
def home():
    return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '')

        account = User.query.filter(db.func.lower(User.name) == name.lower()).first()
        role = account.role if account else None
        if not account:
            account = Student.query.filter(db.func.lower(Student.name) == name.lower()).first()
            role = 'student' if account else None

        if account and account.check_password(password):
            session['role'] = role
            session['user_id'] = account.id
            session['name'] = account.name
            return redirect(url_for(DASHBOARD_ROUTES[role]))

        error = "Invalid name or password."
        return render_template('login.html', error=error, name=name)
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Lets a user ask the administrators for a password reset. There is no email service, so an
    admin generates a temporary password (like Register Student does) and hands it over."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()

        if not name or not email:
            error = "Please enter both your name and email address."
            return render_template('forgot_password.html', error=error, name=name, email=email)

        account = User.query.filter(
            db.func.lower(User.name) == name.lower(), db.func.lower(User.email) == email.lower(),
        ).first()
        role = account.role if account else None
        if not account:
            account = Student.query.filter(
                db.func.lower(Student.name) == name.lower(), db.func.lower(Student.email) == email.lower(),
            ).first()
            role = 'student' if account else None

        if account:
            already_pending = PasswordResetRequest.query.filter_by(
                account_role=role, account_id=account.id, status='Pending',
            ).first()
            if not already_pending:
                db.session.add(PasswordResetRequest(
                    account_role=role, account_id=account.id, name=account.name, email=account.email,
                    status='Pending', requested_at=datetime.now().isoformat(timespec='minutes'),
                ))
                db.session.commit()

        # Same message whether or not the account exists, so this page can't be used to discover accounts.
        return render_template('forgot_password.html', submitted=True)
    return render_template('forgot_password.html')


@app.route('/admin')
@login_required('admin')
def admin_dashboard():
    student_count = Student.query.count()
    issued_count = Certificate.query.count()
    revoked_count = Certificate.query.filter_by(status='Revoked').count()
    verified_count = VerificationRecord.query.filter_by(result='Verified').count()
    recent_certs = sorted(
        Certificate.query.all(),
        key=lambda c: c.revoked_date or c.issued_date or '',
        reverse=True,
    )[:3]
    notifications = attach_notification_links(Notification.query.filter_by(
        recipient_role='admin', recipient_id=session['user_id'],
    ).order_by(Notification.created_at.desc()).all(), 'admin')
    return render_template(
        'admin_dashboard.html',
        student_count=student_count,
        issued_count=issued_count,
        revoked_count=revoked_count,
        verified_count=verified_count,
        recent_certs=recent_certs,
        notifications=notifications,
        pending_reset_count=PasswordResetRequest.query.filter_by(status='Pending').count(),
    )

@app.route('/admin/overview/<category>')
@login_required('admin')
def admin_overview(category):
    if category == 'students':
        students = Student.query.all()
        data = {
            'title': 'Students',
            'total': len(students),
            'columns': ['Student ID', 'Name', 'Program', 'Status'],
            'rows': [[s.student_id, s.name, s.program, s.status] for s in students],
        }
    elif category == 'certificates-issued':
        certs = Certificate.query.all()
        data = {
            'title': 'Certificates Issued',
            'total': len(certs),
            'columns': ['Certificate ID', 'Student', 'Course', 'Date Issued'],
            'rows': [[c.id, c.student, c.course, c.issued_date] for c in certs],
        }
    elif category == 'revoked-certificates':
        certs = Certificate.query.filter_by(status='Revoked').all()
        data = {
            'title': 'Revoked Certificates',
            'total': len(certs),
            'columns': ['Certificate ID', 'Student', 'Reason', 'Date Revoked'],
            'rows': [[c.id, c.student, c.comments, c.revoked_date] for c in certs],
        }
    elif category == 'verified-certificates':
        records = VerificationRecord.query.filter_by(result='Verified').all()
        data = {
            'title': 'Verified Certificates',
            'total': len(records),
            'columns': ['Certificate ID', 'Student', 'Verified By', 'Date Verified'],
            'rows': [[r.cert_id, r.student, r.institution, r.date] for r in records],
        }
    else:
        abort(404, description="Category not found")
    return render_template('overview_detail.html', data=data, category=category)

@app.route('/admin/register-student', methods=['GET', 'POST'])
@login_required('admin')
def register_student():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        program = request.form.get('program', '').strip()
        faculty = request.form.get('faculty', '').strip()
        graduation_year = request.form.get('graduation_year', '').strip()

        if not full_name or not email or not program:
            error = "Full name, email, and program are required."
            return render_template('register_student.html', error=error)

        temp_password = generate_temp_password()
        student = Student(
            student_id=next_student_id(), name=full_name, email=email, phone=phone,
            program=program, faculty=faculty, graduation_year=graduation_year,
            status='Enrolled',
        )
        student.set_password(temp_password)
        db.session.add(student)
        db.session.commit()

        return render_template(
            'register_student.html',
            success=True, new_student=student, temp_password=temp_password,
        )
    return render_template('register_student.html')


@app.route('/admin/issue-certificate', methods=['GET', 'POST'])
@login_required('admin')
def issue_certificate():
    students = Student.query.all()
    if request.method == 'POST':
        student_id = request.form.get('student', '')
        qualification = request.form.get('qualification', '').strip()
        classification = request.form.get('classification', '').strip()
        issue_date = request.form.get('issue_date', '').strip()

        student = Student.query.filter_by(student_id=student_id).first()
        if not student or not qualification or not issue_date:
            error = "Please select a student and fill in qualification and issue date."
            return render_template('issue_certificate.html', students=students, error=error)

        cert_id = next_cert_id()
        file_hash = None
        certificate_file = request.files.get('certificate_file')
        if certificate_file and certificate_file.filename:
            filename, file_hash, file_error = save_certificate_file(certificate_file, cert_id)
            if file_error:
                return render_template('issue_certificate.html', students=students, error=file_error)
        else:
            filename = None

        cert = Certificate(
            id=cert_id, student_fk=student, course=qualification, classification=classification,
            status='Active', issued_date=issue_date, file_path=filename, file_hash=file_hash,
            issued_by_admin_id=session['user_id'],
        )
        db.session.add(cert)
        db.session.commit()
        block = add_certificate_block(cert)

        return render_template(
            'issue_certificate.html', students=students,
            success=True, new_cert=cert, block=block,
        )
    return render_template('issue_certificate.html', students=students)


@app.route('/admin/manage-certificates')
@login_required('admin')
def manage_certificates():
    query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '')
    results = Certificate.query.all()
    if query:
        q_lower = query.lower()
        results = [
            cert for cert in results
            if q_lower in cert.student_id.lower()
            or q_lower in cert.student.lower()
            or q_lower in cert.id.lower()
            or q_lower in cert.course.lower()
        ]
    if status_filter == 'active':
        results = [cert for cert in results if cert.status == 'Active']
    elif status_filter == 'revoked':
        results = [cert for cert in results if cert.status == 'Revoked']
    return render_template(
        'manage_certificates.html', certificates=results, query=query, status_filter=status_filter,
    )

@app.route('/admin/activity')
@login_required('admin')
def admin_activity_all():
    return render_template('activity_all.html', certificates=Certificate.query.all())


@app.route('/admin/activity/<student_id>')
@login_required('admin')
def admin_activity_detail(student_id):
    student = Student.query.filter_by(student_id=student_id).first()
    cert = Certificate.query.filter_by(student_id_fk=student.id).first() if student else None
    if not cert:
        abort(404, description="Student not found")
    return render_template('activity_detail.html', cert=cert)

@app.route('/admin/students')
@login_required('admin')
def admin_students():
    status_filter = request.args.get('status', '')
    students = Student.query.all()
    if status_filter == 'enrolled':
        students = [s for s in students if s.status == 'Enrolled']
    elif status_filter == 'not-enrolled':
        students = [s for s in students if s.status == 'Not Enrolled']
    enrolled_count = Student.query.filter_by(status='Enrolled').count()
    not_enrolled_count = Student.query.filter_by(status='Not Enrolled').count()
    return render_template(
        'students.html', students=students, status_filter=status_filter,
        enrolled_count=enrolled_count, not_enrolled_count=not_enrolled_count
    )


@app.route('/admin/students/<student_id>')
@login_required('admin')
def admin_student_detail(student_id):
    student = Student.query.filter_by(student_id=student_id).first()
    if not student:
        abort(404, description="Student not found")
    return render_template('student_detail.html', student=student)


@app.route('/admin/students/<student_id>/remove', methods=['POST'])
@login_required('admin')
def admin_student_remove(student_id):
    student = Student.query.filter_by(student_id=student_id).first()
    if student:
        db.session.delete(student)
        db.session.commit()
    return redirect(url_for('admin_students'))


@app.route('/admin/certificates')
@login_required('admin')
def admin_certificates():
    status_filter = request.args.get('status', '')
    certs = Certificate.query.all()
    if status_filter == 'active':
        certs = [c for c in certs if c.status == 'Active']
    elif status_filter == 'revoked':
        certs = [c for c in certs if c.status == 'Revoked']
    return render_template('certificates.html', certificates=certs, status_filter=status_filter)


@app.route('/admin/certificates/<cert_id>')
@login_required('admin')
def admin_certificate_detail(cert_id):
    cert = Certificate.query.get(cert_id)
    if not cert:
        abort(404, description="Certificate not found")
    block = Block.query.filter_by(cert_id=cert.id).first()
    verified, verify_reason = verify_certificate(cert)
    return render_template(
        'certificate_detail.html', cert=cert, block=block,
        verified=verified, verify_reason=verify_reason,
    )


@app.route('/admin/certificates/<cert_id>/revoke', methods=['POST'])
@login_required('admin')
def admin_certificate_revoke(cert_id):
    comment = request.form.get('comment', '')
    cert = Certificate.query.get(cert_id)
    if cert:
        cert.status = 'Revoked'
        cert.comments = comment
        db.session.commit()
    return redirect(url_for('admin_certificate_detail', cert_id=cert_id))


@app.route('/admin/certificates/<cert_id>/reinstate', methods=['POST'])
@login_required('admin')
def admin_certificate_reinstate(cert_id):
    comment = request.form.get('comment', '')
    cert = Certificate.query.get(cert_id)
    if cert:
        cert.status = 'Active'
        cert.comments = comment
        db.session.commit()
    return redirect(url_for('admin_certificate_detail', cert_id=cert_id))


@app.route('/admin/blockchain')
@login_required('admin')
def admin_blockchain():
    blocks = Block.query.order_by(Block.index.asc()).all()
    return render_template('blockchain_ledger.html', blocks=blocks)


@app.route('/admin/blockchain/verify', methods=['POST'])
@login_required('admin')
def admin_blockchain_verify():
    blocks = Block.query.order_by(Block.index.asc()).all()
    problems = verify_chain()
    return render_template('blockchain_ledger.html', blocks=blocks, problems=problems, checked=True)


RESET_ROLE_LABELS = {'admin': 'Administrator', 'student': 'Student', 'verifier': 'Verifier'}


def _password_reset_page(**context):
    pending = PasswordResetRequest.query.filter_by(status='Pending') \
        .order_by(PasswordResetRequest.requested_at.desc()).all()
    resolved = PasswordResetRequest.query.filter_by(status='Resolved') \
        .order_by(PasswordResetRequest.resolved_at.desc()).limit(10).all()
    return render_template(
        'password_resets.html', pending=pending, resolved=resolved,
        role_labels=RESET_ROLE_LABELS, **context,
    )


@app.route('/admin/password-resets')
@login_required('admin')
def admin_password_resets():
    return _password_reset_page()


@app.route('/admin/password-resets/<int:request_id>/resolve', methods=['POST'])
@login_required('admin')
def admin_password_reset_resolve(request_id):
    reset_request = PasswordResetRequest.query.get(request_id)
    if not reset_request or reset_request.status != 'Pending':
        return redirect(url_for('admin_password_resets'))

    model = Student if reset_request.account_role == 'student' else User
    account = model.query.get(reset_request.account_id)
    if not account:
        db.session.delete(reset_request)
        db.session.commit()
        return _password_reset_page(error="That account no longer exists, so the request was removed.")

    temp_password = generate_temp_password()
    account.set_password(temp_password)
    reset_request.status = 'Resolved'
    reset_request.resolved_at = datetime.now().isoformat(timespec='minutes')
    db.session.commit()
    return _password_reset_page(reset_request=reset_request, temp_password=temp_password)


@app.route('/admin/profile', methods=['GET', 'POST'])
@login_required('admin')
def admin_profile():
    admin = User.query.get(session['user_id'])
    photo_error = None
    if request.method == 'POST' and admin:
        admin.name = request.form.get('full_name', admin.name)
        session['name'] = admin.name
        admin.email = request.form.get('email', admin.email)
        admin.phone = request.form.get('phone', admin.phone)
        admin.title = request.form.get('title', admin.title)
        admin.bio = request.form.get('bio', admin.bio)
        photo = request.files.get('photo')
        if photo and photo.filename:
            filename, photo_error = save_profile_photo(photo, 'admin', admin.profile_picture)
            if filename:
                admin.profile_picture = filename
        db.session.commit()
    return render_template('admin_profile.html', admin=admin, photo_error=photo_error)


@app.route('/admin/profile/change-password', methods=['POST'])
@login_required('admin')
def admin_change_password():
    admin = User.query.get(session['user_id'])
    password_success, password_error = change_password(admin, request.form)
    return render_template('admin_profile.html', admin=admin, password_success=password_success, password_error=password_error)


def _student_certificates_with_views(student):
    certs = Certificate.query.filter_by(student_id_fk=student.id).all()
    for cert in certs:
        cert.view_count = VerificationRecord.query.filter_by(cert_id=cert.id).count()
    return certs


@app.route('/student')
@login_required('student')
def student_dashboard():
    student = Student.query.get(session['user_id'])
    certificates = _student_certificates_with_views(student)
    notifications = attach_notification_links(Notification.query.filter_by(
        recipient_role='student', recipient_id=student.id,
    ).order_by(Notification.created_at.desc()).all(), 'student')
    return render_template('student_dashboard.html', certificates=certificates, notifications=notifications)

@app.route('/student/certificates')
@login_required('student')
def student_certificates():
    student = Student.query.get(session['user_id'])
    certificates = _student_certificates_with_views(student)
    return render_template('student_certificates.html', certificates=certificates)

@app.route('/student/certificates/add', methods=['GET', 'POST'])
@login_required('student')
def add_student_certificate():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        institution = request.form.get('institution', '').strip()
        year = request.form.get('year', '').strip()

        if not title:
            error = "Certificate title is required."
            return render_template('add_student_certificate.html', error=error)

        student = Student.query.get(session['user_id'])
        cert_id = next_cert_id()
        file_hash = None
        filename = None
        certificate_file = request.files.get('certificate_file')
        if certificate_file and certificate_file.filename:
            filename, file_hash, file_error = save_certificate_file(certificate_file, cert_id)
            if file_error:
                return render_template('add_student_certificate.html', error=file_error)

        cert = Certificate(
            id=cert_id, student_fk=student, course=title, status='Active',
            issued_date=year, issuing_institution=institution, source='student',
            file_path=filename, file_hash=file_hash,
        )
        db.session.add(cert)
        db.session.commit()

        return redirect(url_for('student_certificates'))
    return render_template('add_student_certificate.html')


@app.route('/student/certificates/<cert_id>/remove', methods=['POST'])
@login_required('student')
def remove_student_certificate(cert_id):
    student = Student.query.get(session['user_id'])
    cert = Certificate.query.get(cert_id)
    if cert and cert.student_id_fk == student.id and cert.source == 'student':
        if cert.file_path:
            file_path = os.path.join(CERTIFICATE_UPLOAD_FOLDER, cert.file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
        VerificationRecord.query.filter_by(cert_id=cert.id).delete()
        db.session.delete(cert)
        db.session.commit()
    return redirect(url_for('student_certificates'))


@app.route('/student/certificates/<cert_id>/download')
@login_required('student')
def student_certificate_download(cert_id):
    student = Student.query.get(session['user_id'])
    cert = Certificate.query.get(cert_id)
    if not cert or cert.student_id_fk != student.id or not cert.file_path:
        abort(404, description="Certificate file not found")
    return send_from_directory(
        CERTIFICATE_UPLOAD_FOLDER, cert.file_path,
        as_attachment=True, download_name=f"{cert.id}.pdf",
    )


@app.route('/student/certificates/<cert_id>/qr')
@login_required('student')
def student_certificate_qr(cert_id):
    student = Student.query.get(session['user_id'])
    cert = Certificate.query.get(cert_id)
    if not cert or cert.student_id_fk != student.id:
        abort(404, description="Certificate not found")
    verify_url = url_for('verify_certificate_public', cert_id=cert.id, _external=True)
    return render_template('student_certificate_qr.html', cert=cert, verify_url=verify_url)


@app.route('/student/certificates/<cert_id>/qr.svg')
@login_required('student')
def student_certificate_qr_svg(cert_id):
    student = Student.query.get(session['user_id'])
    cert = Certificate.query.get(cert_id)
    if not cert or cert.student_id_fk != student.id:
        abort(404, description="Certificate not found")
    verify_url = url_for('verify_certificate_public', cert_id=cert.id, _external=True)
    img = qrcode.make(verify_url, image_factory=qrcode.image.svg.SvgImage)
    buffer = io.BytesIO()
    img.save(buffer)
    return Response(buffer.getvalue(), mimetype='image/svg+xml')


@app.route('/student/certificates/<cert_id>/views')
@login_required('student')
def student_certificate_views(cert_id):
    student = Student.query.get(session['user_id'])
    cert = Certificate.query.get(cert_id)
    if not cert or cert.student_id_fk != student.id:
        abort(404, description="Certificate not found")
    records = VerificationRecord.query.filter_by(cert_id=cert.id).all()
    return render_template('student_certificate_views.html', cert=cert, records=records)


@app.route('/student/share')
@login_required('student')
def student_share():
    student = Student.query.get(session['user_id'])
    certificates = Certificate.query.filter_by(student_id_fk=student.id).all()
    for cert in certificates:
        cert.verify_url = url_for('verify_certificate_public', cert_id=cert.id, _external=True)
    return render_template('student_share.html', certificates=certificates)


@app.route('/verify/<cert_id>')
def verify_certificate_public(cert_id):
    cert = Certificate.query.get(cert_id)
    if not cert:
        return render_template('verify_public.html', cert=None)
    verified, verify_reason = (None, None)
    if cert.source == 'admin':
        verified, verify_reason = verify_certificate(cert)
    return render_template('verify_public.html', cert=cert, verified=verified, verify_reason=verify_reason)

@app.route('/student/profile', methods=['GET', 'POST'])
@login_required('student')
def student_profile():
    student = Student.query.get(session['user_id'])
    photo_error = None
    if request.method == 'POST' and student:
        student.name = request.form.get('full_name', student.name)
        session['name'] = student.name
        student.email = request.form.get('email', student.email)
        student.phone = request.form.get('phone', student.phone)
        student.program = request.form.get('program', student.program)
        student.bio = request.form.get('bio', student.bio)
        photo = request.files.get('photo')
        if photo and photo.filename:
            filename, photo_error = save_profile_photo(photo, 'student', student.profile_picture)
            if filename:
                student.profile_picture = filename
        db.session.commit()
    return render_template('student_profile.html', student=student, photo_error=photo_error)


@app.route('/student/profile/change-password', methods=['POST'])
@login_required('student')
def student_change_password():
    student = Student.query.get(session['user_id'])
    password_success, password_error = change_password(student, request.form)
    return render_template('student_profile.html', student=student, password_success=password_success, password_error=password_error)

@app.route('/verifier', methods=['GET', 'POST'])
@login_required('verifier')
def verifier_dashboard():
    notifications = attach_notification_links(Notification.query.filter_by(
        recipient_role='verifier', recipient_id=session['user_id'],
    ).order_by(Notification.created_at.desc()).all(), 'verifier')

    if request.method == 'POST':
        cert_id = request.form.get('cert_id', '').strip()
        verifier = User.query.get(session['user_id'])
        cert = Certificate.query.get(cert_id)

        if not cert:
            result = 'Failed'
            reason = 'Certificate number not found in registry.'
        elif cert.status == 'Revoked':
            result = 'Failed'
            reason = 'Certificate has been revoked by the issuing institution.'
        else:
            result = 'Verified'
            reason = ''

        record = VerificationRecord(
            id=next_verification_id(), cert_id=cert_id,
            student=cert.student if cert else 'Unknown',
            qualification=cert.course if cert else 'Unknown',
            institution=verifier.organization, date=date.today().isoformat(),
            result=result, reason=reason,
        )
        db.session.add(record)
        db.session.commit()

        return render_template(
            'verifier_dashboard.html', cert=cert, result=result, reason=reason,
            searched_id=cert_id, notifications=notifications,
        )
    return render_template('verifier_dashboard.html', notifications=notifications)

@app.route('/verifier/history')
@login_required('verifier')
def verifier_history():
    verifier = User.query.get(session['user_id'])
    history = VerificationRecord.query.filter_by(institution=verifier.organization).all()
    return render_template('verifier_history.html', history=history)

@app.route('/verifier/history/<record_id>')
@login_required('verifier')
def verifier_history_detail(record_id):
    verifier = User.query.get(session['user_id'])
    record = VerificationRecord.query.get(record_id)
    if not record or record.institution != verifier.organization:
        abort(404, description="Record not found")
    return render_template('verifier_history_detail.html', record=record)

@app.route('/verifier/share')
@login_required('verifier')
def verifier_share():
    verifier = User.query.get(session['user_id'])
    history = VerificationRecord.query.filter_by(institution=verifier.organization).all()
    return render_template(
        'verifier_share.html', history=history,
        sent_record=request.args.get('sent_record'), sent_target=request.args.get('sent_target'),
    )


TARGET_LABELS = {'school': 'School', 'student': 'Student', 'other_verifiers': 'Other Verifiers'}


@app.route('/verifier/share/<record_id>/send', methods=['POST'])
@login_required('verifier')
def send_verification_share(record_id):
    verifier = User.query.get(session['user_id'])
    record = VerificationRecord.query.get(record_id)
    target = request.form.get('target', '')

    if record and target in TARGET_LABELS:
        cert = Certificate.query.get(record.cert_id)
        message = (
            f"{verifier.organization} shared a verification result for "
            f"{record.cert_id} ({record.student}) — {record.result}."
        )
        timestamp = datetime.now().isoformat()

        if target == 'school':
            admin_ids = [cert.issued_by_admin_id] if cert and cert.issued_by_admin_id else \
                [a.id for a in User.query.filter_by(role='admin').all()]
            for admin_id in admin_ids:
                db.session.add(Notification(
                    recipient_role='admin', recipient_id=admin_id, record_id=record.id,
                    cert_id=record.cert_id, message=message, created_at=timestamp,
                ))
        elif target == 'student' and cert:
            db.session.add(Notification(
                recipient_role='student', recipient_id=cert.student_fk.id, record_id=record.id,
                cert_id=record.cert_id, message=message, created_at=timestamp,
            ))
        elif target == 'other_verifiers':
            for other in User.query.filter_by(role='verifier').all():
                if other.id != verifier.id:
                    db.session.add(Notification(
                        recipient_role='verifier', recipient_id=other.id, record_id=record.id,
                        cert_id=record.cert_id, message=message, created_at=timestamp,
                    ))
        db.session.commit()

    return redirect(url_for('verifier_share', sent_record=record_id, sent_target=target))

@app.route('/verifier/profile', methods=['GET', 'POST'])
@login_required('verifier')
def verifier_profile():
    verifier = User.query.get(session['user_id'])
    photo_error = None
    if request.method == 'POST' and verifier:
        verifier.name = request.form.get('full_name', verifier.name)
        session['name'] = verifier.name
        verifier.email = request.form.get('email', verifier.email)
        verifier.phone = request.form.get('phone', verifier.phone)
        verifier.organization = request.form.get('organization', verifier.organization)
        verifier.bio = request.form.get('bio', verifier.bio)
        photo = request.files.get('photo')
        if photo and photo.filename:
            filename, photo_error = save_profile_photo(photo, 'verifier', verifier.profile_picture)
            if filename:
                verifier.profile_picture = filename
        db.session.commit()
    return render_template('verifier_profile.html', verifier=verifier, photo_error=photo_error)


@app.route('/verifier/profile/change-password', methods=['POST'])
@login_required('verifier')
def verifier_change_password():
    verifier = User.query.get(session['user_id'])
    password_success, password_error = change_password(verifier, request.form)
    return render_template('verifier_profile.html', verifier=verifier, password_success=password_success, password_error=password_error)

@app.errorhandler(404)
def not_found(error):
    home_endpoint = DASHBOARD_ROUTES.get(session.get('role'), 'login')
    return render_template('not_found.html', description=error.description, home_endpoint=home_endpoint), 404


if __name__ == '__main__':
    app.run(debug=True)
