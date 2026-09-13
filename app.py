from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

OVERVIEW_DATA = {
    'students': {
        'title': 'Students',
        'total': 546,
        'columns': ['Student ID', 'Name', 'Program', 'Status'],
        'rows': [
            ['STU-1042', 'Mac Daniel', 'BSc Information Technology', 'Active'],
            ['STU-1043', 'Jan Allan', 'Diploma in Information Technology', 'Active'],
            ['STU-1044', 'James Aron', 'BSc Computer Science', 'Active'],
        ],
    },
    'certificates-issued': {
        'title': 'Certificates Issued',
        'total': 736,
        'columns': ['Certificate ID', 'Student', 'Course', 'Date Issued'],
        'rows': [
            ['CERT-8821', 'Mac Daniel', 'BSc Information Technology', 'Jun 14, 2025'],
            ['CERT-8830', 'James Aron', 'BSc Computer Science', 'Nov 2, 2025'],
            ['CERT-8834', 'Priya Nathan', 'Diploma in Business', 'Nov 8, 2025'],
        ],
    },
    'revoked-certificates': {
        'title': 'Revoked Certificates',
        'total': 211,
        'columns': ['Certificate ID', 'Student', 'Reason', 'Date Revoked'],
        'rows': [
            ['CERT-7710', 'Jan Allan', 'Academic misconduct', 'Aug 3, 2025'],
            ['CERT-7745', 'Kevin Watu', 'Issued in error', 'Sep 19, 2025'],
        ],
    },
    'verified-certificates': {
        'title': 'Verified Certificates',
        'total': 571,
        'columns': ['Certificate ID', 'Student', 'Verified By', 'Date Verified'],
        'rows': [
            ['CERT-8821', 'Mac Daniel', 'Acme Corp HR', 'Jul 1, 2025'],
            ['CERT-8834', 'Priya Nathan', 'Global Bank Ltd', 'Nov 10, 2025'],
        ],
    },
}

SAMPLE_CERTIFICATES = [
    {'id': 'CERT-8821', 'student_id': 'STU-1042', 'student': 'Mac Daniel', 'course': 'BSc Information Technology', 'status': 'Active', 'comments': ''},
    {'id': 'CERT-8830', 'student_id': 'STU-1044', 'student': 'James Aron', 'course': 'BSc Computer Science', 'status': 'Active', 'comments': ''},
    {'id': 'CERT-7710', 'student_id': 'STU-1043', 'student': 'Jan Allan', 'course': 'Diploma in Information Technology', 'status': 'Revoked', 'comments': ''},
    {'id': 'CERT-8834', 'student_id': 'STU-1045', 'student': 'Priya Nathan', 'course': 'Diploma in Business', 'status': 'Active', 'comments': ''},
]

STUDENTS = [
    {
        'student_id': 'STU-1042', 'name': 'Mac Daniel', 'program': 'BSc Information Technology',
        'status': 'Enrolled',
        'previous_schools': [
            {'school': 'Port Moresby Grammar School', 'certificate': 'Grade 12 Certificate', 'year': '2021'},
        ],
    },
    {
        'student_id': 'STU-1043', 'name': 'Jan Allan', 'program': 'Diploma in Information Technology',
        'status': 'Not Enrolled',
        'previous_schools': [
            {'school': 'Sacred Heart High School', 'certificate': 'Grade 12 Certificate', 'year': '2020'},
        ],
    },
    {
        'student_id': 'STU-1044', 'name': 'James Aron', 'program': 'BSc Computer Science',
        'status': 'Enrolled',
        'previous_schools': [
            {'school': 'Kerevat National High School', 'certificate': 'Grade 12 Certificate', 'year': '2022'},
        ],
    },
    {
        'student_id': 'STU-1045', 'name': 'Priya Nathan', 'program': 'Diploma in Business',
        'status': 'Enrolled',
        'previous_schools': [],
    },
    {
        'student_id': 'STU-1046', 'name': 'Kevin Watu', 'program': 'BSc Information Technology',
        'status': 'Not Enrolled',
        'previous_schools': [
            {'school': 'Aiyura National High School', 'certificate': 'Grade 12 Certificate', 'year': '2019'},
        ],
    },
]

ADMIN_PROFILE = {
    'name': 'Admin User',
    'email': 'admin@acvs.edu',
    'phone': '',
    'title': 'System Administrator',
    'bio': '',
    'initials': 'AU',
}


@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.route('/admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin/overview/<category>')
def admin_overview(category):
    data = OVERVIEW_DATA.get(category)
    if not data:
        return "Category not found", 404
    return render_template('overview_detail.html', data=data, category=category)

@app.route('/admin/register-student', methods=['GET', 'POST'])
def register_student():
    return render_template('register_student.html')


@app.route('/admin/issue-certificate', methods=['GET', 'POST'])
def issue_certificate():
    return render_template('issue_certificate.html')


@app.route('/admin/manage-certificates')
def manage_certificates():
    query = request.args.get('q', '').strip()
    results = SAMPLE_CERTIFICATES
    if query:
        q_lower = query.lower()
        results = [
            cert for cert in SAMPLE_CERTIFICATES
            if q_lower in cert['student_id'].lower()
            or q_lower in cert['student'].lower()
            or q_lower in cert['id'].lower()
            or q_lower in cert['course'].lower()
        ]
    return render_template('manage_certificates.html', certificates=results, query=query)

@app.route('/admin/activity')
def admin_activity_all():
    return render_template('activity_all.html', certificates=SAMPLE_CERTIFICATES)


@app.route('/admin/activity/<student_id>')
def admin_activity_detail(student_id):
    cert = next((c for c in SAMPLE_CERTIFICATES if c['student_id'] == student_id), None)
    if not cert:
        return "Student not found", 404
    return render_template('activity_detail.html', cert=cert)

@app.route('/admin/students')
def admin_students():
    status_filter = request.args.get('status', '')
    students = STUDENTS
    if status_filter == 'enrolled':
        students = [s for s in STUDENTS if s['status'] == 'Enrolled']
    elif status_filter == 'not-enrolled':
        students = [s for s in STUDENTS if s['status'] == 'Not Enrolled']
    enrolled_count = sum(1 for s in STUDENTS if s['status'] == 'Enrolled')
    not_enrolled_count = sum(1 for s in STUDENTS if s['status'] == 'Not Enrolled')
    return render_template(
        'students.html', students=students, status_filter=status_filter,
        enrolled_count=enrolled_count, not_enrolled_count=not_enrolled_count
    )


@app.route('/admin/students/<student_id>')
def admin_student_detail(student_id):
    student = next((s for s in STUDENTS if s['student_id'] == student_id), None)
    if not student:
        return "Student not found", 404
    return render_template('student_detail.html', student=student)


@app.route('/admin/students/<student_id>/remove', methods=['POST'])
def admin_student_remove(student_id):
    global STUDENTS
    STUDENTS = [s for s in STUDENTS if s['student_id'] != student_id]
    return redirect(url_for('admin_students'))


@app.route('/admin/certificates')
def admin_certificates():
    status_filter = request.args.get('status', '')
    certs = SAMPLE_CERTIFICATES
    if status_filter == 'active':
        certs = [c for c in SAMPLE_CERTIFICATES if c['status'] == 'Active']
    elif status_filter == 'revoked':
        certs = [c for c in SAMPLE_CERTIFICATES if c['status'] == 'Revoked']
    return render_template('certificates.html', certificates=certs, status_filter=status_filter)


@app.route('/admin/certificates/<cert_id>')
def admin_certificate_detail(cert_id):
    cert = next((c for c in SAMPLE_CERTIFICATES if c['id'] == cert_id), None)
    if not cert:
        return "Certificate not found", 404
    return render_template('certificate_detail.html', cert=cert)


@app.route('/admin/certificates/<cert_id>/revoke', methods=['POST'])
def admin_certificate_revoke(cert_id):
    comment = request.form.get('comment', '')
    for c in SAMPLE_CERTIFICATES:
        if c['id'] == cert_id:
            c['status'] = 'Revoked'
            c['comments'] = comment
    return redirect(url_for('admin_certificate_detail', cert_id=cert_id))


@app.route('/admin/certificates/<cert_id>/reinstate', methods=['POST'])
def admin_certificate_reinstate(cert_id):
    comment = request.form.get('comment', '')
    for c in SAMPLE_CERTIFICATES:
        if c['id'] == cert_id:
            c['status'] = 'Active'
            c['comments'] = comment
    return redirect(url_for('admin_certificate_detail', cert_id=cert_id))


@app.route('/admin/profile', methods=['GET', 'POST'])
def admin_profile():
    if request.method == 'POST':
        ADMIN_PROFILE['name'] = request.form.get('full_name', ADMIN_PROFILE['name'])
        ADMIN_PROFILE['email'] = request.form.get('email', ADMIN_PROFILE['email'])
        ADMIN_PROFILE['phone'] = request.form.get('phone', ADMIN_PROFILE['phone'])
        ADMIN_PROFILE['title'] = request.form.get('title', ADMIN_PROFILE['title'])
        ADMIN_PROFILE['bio'] = request.form.get('bio', ADMIN_PROFILE['bio'])
    return render_template('admin_profile.html', admin=ADMIN_PROFILE)


@app.route('/student')
def student_dashboard():
    return render_template('student_dashboard.html')

@app.route('/verifier')
def verifier_dashboard():
    return render_template('verifier_dashboard.html')

if __name__ == '__main__':
    app.run(debug=True)