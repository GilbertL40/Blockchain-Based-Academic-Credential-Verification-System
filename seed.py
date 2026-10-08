"""Resets the database and populates it with demo data matching the templates.

Run with: python seed.py
"""

import secrets
import string

from app import app
from models import db, User, Student, PreviousSchool, Certificate, VerificationRecord
from blockchain import add_certificate_block

PASSWORD_ALPHABET = string.ascii_letters + string.digits


def random_password(length=10):
    return ''.join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))

ADMINS = [
    ('Vinet Pius', 'vinet.pius@acvs.edu', 'System Administrator'),
    ('Teddy Bauwa', 'teddy.bauwa@acvs.edu', 'Academic Registrar'),
    ('Martha Oswald', 'martha.oswald@acvs.edu', 'Deputy Registrar'),
    ('Francis Kaupa', 'francis.kaupa@acvs.edu', 'IT Systems Manager'),
    ('Helen Namaliu', 'helen.namaliu@acvs.edu', 'System Administrator'),
    ('Robert Kuman', 'robert.kuman@acvs.edu', 'Records Officer'),
    ('Josephine Agiru', 'josephine.agiru@acvs.edu', 'Academic Registrar'),
    ('Peter Isaac', 'peter.isaac@acvs.edu', 'System Administrator'),
    ('Grace Pulayasi', 'grace.pulayasi@acvs.edu', 'Records Officer'),
    ('Michael Somare', 'michael.somare@acvs.edu', 'Deputy Registrar'),
    ('Alice Wartoto', 'alice.wartoto@acvs.edu', 'IT Systems Manager'),
    ('Daniel Koim', 'daniel.koim@acvs.edu', 'System Administrator'),
]

VERIFIERS = [
    ('Daniel July', 'daniel.july@acmecorp.com', 'Acme Corp HR'),
    ('Alex Morgan', 'alex.morgan@acmecorp.com', 'Acme Corp HR'),
    ('Nancy Sapau', 'nancy.sapau@globalbank.com', 'Global Bank Ltd'),
    ('Oscar Tomscoll', 'oscar.tomscoll@digicelpng.com', 'Digicel PNG'),
    ('Patricia Sine', 'patricia.sine@bsp.com.pg', 'BSP Financial Group'),
    ('Benjamin Poya', 'benjamin.poya@steamships.com.pg', 'Steamships Trading'),
    ('Carol Yama', 'carol.yama@oilsearch.com', 'Oil Search Ltd'),
    ('Henry Degemba', 'henry.degemba@airniugini.com.pg', 'Air Niugini'),
    ('Irene Kilepak', 'irene.kilepak@bankpng.gov.pg', 'Bank of PNG'),
    ('Wesley Undi', 'wesley.undi@creditcorp.com.pg', 'Credit Corporation'),
    ('Fiona Gawi', 'fiona.gawi@nasfund.com.pg', 'Nasfund'),
    ('Samuel Taufa', 'samuel.taufa@kinabank.com.pg', 'Kina Bank'),
]

# (student_id, name, program, status, previous_school or None)
STUDENTS = [
    ('STU-1042', 'Mac Daniel', 'BSc Information Technology', 'Enrolled',
     ('Port Moresby Grammar School', 'Grade 12 Certificate', '2021')),
    ('STU-1043', 'Jan Allan', 'Diploma in Information Technology', 'Not Enrolled',
     ('Sacred Heart High School', 'Grade 12 Certificate', '2020')),
    ('STU-1044', 'James Aron', 'BSc Computer Science', 'Enrolled',
     ('Kerevat National High School', 'Grade 12 Certificate', '2022')),
    ('STU-1045', 'Priya Nathan', 'Diploma in Business', 'Enrolled', None),
    ('STU-1046', 'Kevin Watu', 'BSc Information Technology', 'Not Enrolled',
     ('Aiyura National High School', 'Grade 12 Certificate', '2019')),
    ('STU-1047', 'Mohnne Temon', 'BSc Computer Science', 'Enrolled',
     ('Sogeri National High School', 'Grade 12 Certificate', '2021')),
    ('STU-1048', 'Jaden Kobal', 'Diploma in Business', 'Enrolled',
     ('Marianville Secondary School', 'Grade 12 Certificate', '2020')),
    ('STU-1049', 'Grace Elly', 'BSc Information Technology', 'Enrolled',
     ('Port Moresby International School', 'Grade 12 Certificate', '2022')),
    ('STU-1050', 'Thomas Siga', 'Diploma in Information Technology', 'Not Enrolled',
     ('Kimbe International School', 'Grade 12 Certificate', '2018')),
    ('STU-1051', 'Rachel Buri', 'BSc Accounting', 'Enrolled',
     ("St. Joseph's International School", 'Grade 12 Certificate', '2021')),
    ('STU-1052', 'Simon Kaupa', 'BSc Computer Science', 'Enrolled',
     ('Gordons Secondary School', 'Grade 12 Certificate', '2022')),
    ('STU-1053', 'Lucy Waigani', 'Diploma in Business', 'Not Enrolled', None),
]

# (cert_id, student_id, course, status, issued_date, revoked_date, comments)
CERTIFICATES = [
    ('CERT-8821', 'STU-1042', 'BSc Information Technology', 'Active', '2025-06-14', '', ''),
    ('CERT-8822', 'STU-1042', 'Networking Fundamentals', 'Active', '2025-07-01', '', ''),
    ('CERT-7710', 'STU-1043', 'Diploma in Information Technology', 'Revoked', '2024-05-10', '2025-08-03', 'Academic misconduct'),
    ('CERT-8830', 'STU-1044', 'BSc Computer Science', 'Active', '2025-11-02', '', ''),
    ('CERT-8831', 'STU-1044', 'Database Systems', 'Active', '2025-11-20', '', ''),
    ('CERT-8834', 'STU-1045', 'Diploma in Business', 'Active', '2025-11-08', '', ''),
    ('CERT-7745', 'STU-1046', 'BSc Information Technology', 'Revoked', '2024-09-01', '2025-09-19', 'Issued in error'),
    ('CERT-8840', 'STU-1047', 'BSc Computer Science', 'Active', '2025-09-05', '', ''),
    ('CERT-8841', 'STU-1047', 'Software Engineering', 'Active', '2025-09-25', '', ''),
    ('CERT-8845', 'STU-1048', 'Diploma in Business', 'Active', '2025-10-01', '', ''),
    ('CERT-8850', 'STU-1049', 'BSc Information Technology', 'Active', '2025-10-10', '', ''),
    ('CERT-8851', 'STU-1049', 'Web Development', 'Revoked', '2025-03-01', '2025-10-15', 'Duplicate submission'),
    ('CERT-7760', 'STU-1050', 'Diploma in Information Technology', 'Revoked', '2024-02-01', '2025-04-12', 'Academic misconduct'),
    ('CERT-8860', 'STU-1051', 'BSc Accounting', 'Active', '2025-08-18', '', ''),
    ('CERT-8861', 'STU-1051', 'Financial Reporting', 'Active', '2025-09-30', '', ''),
    ('CERT-8865', 'STU-1052', 'BSc Computer Science', 'Active', '2025-07-22', '', ''),
    ('CERT-7770', 'STU-1053', 'Diploma in Business', 'Revoked', '2024-11-11', '2025-05-05', 'Issued in error'),
]

# (record_id, cert_id, student, qualification, institution, date, result, reason)
VERIFICATION_RECORDS = [
    ('VER-3001', 'CERT-8821', 'Mac Daniel', 'BSc Information Technology', 'Acme Corp HR', '2025-07-01', 'Verified', ''),
    ('VER-3002', 'CERT-8830', 'James Aron', 'BSc Computer Science', 'Global Bank Ltd', '2025-11-10', 'Verified', ''),
    ('VER-3003', 'CERT-9911', 'Kevin Watu', 'Diploma in Business', 'Unknown Institution', '2025-09-14', 'Failed', 'Certificate number not found in registry.'),
    ('VER-3004', 'CERT-8834', 'Priya Nathan', 'Diploma in Business', 'Digicel PNG', '2025-11-12', 'Verified', ''),
    ('VER-3005', 'CERT-7710', 'Jan Allan', 'Diploma in Information Technology', 'BSP Financial Group', '2025-08-05', 'Failed', 'Certificate has been revoked by the issuing institution.'),
    ('VER-3006', 'CERT-8840', 'Mohnne Temon', 'BSc Computer Science', 'Steamships Trading', '2025-09-10', 'Verified', ''),
    ('VER-3007', 'CERT-8845', 'Jaden Kobal', 'Diploma in Business', 'Oil Search Ltd', '2025-10-05', 'Verified', ''),
    ('VER-3008', 'CERT-8850', 'Grace Elly', 'BSc Information Technology', 'Air Niugini', '2025-10-14', 'Verified', ''),
    ('VER-3009', 'CERT-7745', 'Kevin Watu', 'BSc Information Technology', 'Bank of PNG', '2025-09-20', 'Failed', 'Certificate has been revoked by the issuing institution.'),
    ('VER-3010', 'CERT-8860', 'Rachel Buri', 'BSc Accounting', 'Credit Corporation', '2025-08-22', 'Verified', ''),
    ('VER-3011', 'CERT-8865', 'Simon Kaupa', 'BSc Computer Science', 'Kina Bank', '2025-07-28', 'Verified', ''),
]


def seed():
    db.drop_all()
    db.create_all()

    credentials = []
    first_admin = None

    for name, email, title in ADMINS:
        password = random_password()
        user = User(name=name, email=email, role='admin', title=title)
        user.set_password(password)
        db.session.add(user)
        credentials.append((name, 'admin', password))
        if first_admin is None:
            first_admin = user

    for name, email, organization in VERIFIERS:
        password = random_password()
        user = User(name=name, email=email, role='verifier', organization=organization)
        user.set_password(password)
        db.session.add(user)
        credentials.append((name, 'verifier', password))

    students_by_id = {}
    for student_id, name, program, status, school in STUDENTS:
        password = random_password()
        email = name.lower().replace(' ', '.') + '@student.acvs.edu'
        student = Student(student_id=student_id, name=name, program=program, status=status, email=email)
        student.set_password(password)
        db.session.add(student)
        students_by_id[student_id] = student
        credentials.append((name, 'student', password))
        if school:
            school_name, certificate, year = school
            db.session.add(PreviousSchool(student=student, school=school_name, certificate=certificate, year=year))

    db.session.flush()  # assigns first_admin.id so it can be used below

    for cert_id, student_id, course, status, issued_date, revoked_date, comments in CERTIFICATES:
        db.session.add(Certificate(
            id=cert_id, student_fk=students_by_id[student_id], course=course,
            status=status, issued_date=issued_date, revoked_date=revoked_date, comments=comments,
            issued_by_admin_id=first_admin.id,
        ))

    for record_id, cert_id, student, qualification, institution, date, result, reason in VERIFICATION_RECORDS:
        db.session.add(VerificationRecord(
            id=record_id, cert_id=cert_id, student=student, qualification=qualification,
            institution=institution, date=date, result=result, reason=reason,
        ))

    db.session.commit()

    for cert in Certificate.query.order_by(Certificate.issued_date.asc()).all():
        add_certificate_block(cert)

    with open('credentials.txt', 'w', encoding='utf-8') as f:
        f.write("Name                      Role       Password\n")
        f.write("-" * 50 + "\n")
        for name, role, password in credentials:
            f.write(f"{name:<25} {role:<10} {password}\n")

    print(f"Admins: {User.query.filter_by(role='admin').count()}")
    print(f"Verifiers: {User.query.filter_by(role='verifier').count()}")
    print(f"Students: {Student.query.count()}")
    print(f"Previous schools: {PreviousSchool.query.count()}")
    print(f"Certificates: {Certificate.query.count()}")
    print(f"Verification records: {VerificationRecord.query.count()}")
    from blockchain import Block
    print(f"Blockchain blocks: {Block.query.count()}")
    print("Login credentials written to credentials.txt")


if __name__ == '__main__':
    with app.app_context():
        seed()
