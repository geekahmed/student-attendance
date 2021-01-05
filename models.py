import os
from sqlalchemy import Column, String, Integer, create_engine, ForeignKey, DateTime, Boolean, Table
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
import json
import datetime
from sqlalchemy.ext.declarative import declarative_base

database_filename = "database.db"
project_dir = os.path.dirname(os.path.abspath(__file__))
database_path = "sqlite:///{}".format(os.path.join(project_dir, database_filename))

db = SQLAlchemy()
Base = declarative_base()


def setup_db(app):
    app.config["SQLALCHEMY_DATABASE_URI"] = database_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.app = app
    db.init_app(app)


def db_drop_and_create_all():
    db.drop_all()
    db.create_all()


class Course(db.Model):
    __tablename__ = 'course'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    code = Column(String, unique=True, nullable=False)
    grade = Column(String)
    teacher_id = Column(ForeignKey('teacher.id'))
    teacher = relationship('Teacher', back_populates="courses")


    students = relationship('Attendance', back_populates='course')

    def __init__(self, name, code, grade):
        self.name = name
        self.code = code
        self.grade = grade

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def format(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'grade': self.grade
        }


class User(db.Model):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    phone = Column(String, unique=True, nullable=False)
    type = Column(String)

    __mapper_args__ = {
        "polymorphic_identity": "user",
        "polymorphic_on": type,
    }

    def __init__(self, first_name, last_name, email, password, phone, type):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.password = password
        self.phone = phone
        self.type = type

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def format(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone
        }


class Teacher(User):
    __tablename__ = 'teacher'
    id = Column(ForeignKey('user.id'), primary_key=True)
    __mapper_args__ = {"polymorphic_identity": "teacher"}

    courses = relationship('Course', back_populates='teacher')


class Student(User):
    __tablename__ = 'student'
    id = Column(ForeignKey('user.id'), primary_key=True)
    university_id = Column(String, unique=True)
    __mapper_args__ = {"polymorphic_identity": "student"}

    attendances = relationship('Attendance')
    courses = relationship("Enrollement")
    def __init__(self, university_id, first_name, last_name, email, password, phone, type):
        super().__init__(first_name, last_name, email, password, phone, type)
        self.university_id = university_id

    def format(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'university_id': self.university_id
        }


class Attendance(db.Model):
    __tablename__ = 'attendance'

    student_id = Column(Integer, ForeignKey('student.id'), primary_key=True)
    course_id = Column(Integer, ForeignKey('course.id'), primary_key=True)
    
    attendance_time = Column(DateTime, nullable=False)
    attendance_token = Column(String(500),nullable=False)
    
    course = relationship("Course")

    def __init__(self, attendance_time, attendance_token):
        self.attendance_time = attendance_time
        self.attendance_token = attendance_token

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

class Enrollement(db.Model):
    __tablename__="enroll"

    student_id = Column(Integer, ForeignKey('student.id'), primary_key=True)
    course_id = Column(Integer, ForeignKey('course.id'), primary_key=True)

    course = relationship("Course")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()






class BlacklistToken(db.Model):
    """
    Token Model for storing JWT tokens
    """
    __tablename__ = 'blacklist_tokens'

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(500), unique=True, nullable=False)
    blacklisted_on = Column(DateTime, nullable=False)

    def __init__(self, token):
        self.token = token
        self.blacklisted_on = datetime.datetime.now()

    def __repr__(self):
        return '<id: token: {}'.format(self.token)

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def check_blacklist(auth_token):
        # check whether auth token has been blacklisted
        res = BlacklistToken.query.filter_by(token=str(auth_token)).first()
        if res:
            return True
        else:
            return False
