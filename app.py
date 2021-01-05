from flask import Flask, request, abort, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from models import db, db_drop_and_create_all, setup_db, User, BlacklistToken, Course, Student, Teacher, Attendance, Enrollement
from auth import encode_auth_token, decode_auth_token, requires_auth
from attendance import generate_attendance_code, verify_attendance_code

import datetime


app = Flask(__name__)
app.config['SECRET_KEY'] = "random string"

# Initializing sqlite database
setup_db(app)
CORS(app)

db_drop_and_create_all()


@app.route('/')
def hello():
    return "Hello World!"


@app.route('/signup', methods=['POST'])
def signup():
    body = request.get_json()
    # check if user already exists
    user = User.query.filter_by(email=body.get('email')).first()
    if not user:
        user_first_name = body.get('first_name')
        user_last_name = body.get('last_name')
        user_email = body.get('email')
        user_phone = body.get('phone')
        user_university_id = body.get('university_id')
        if (user_first_name is None) or (user_last_name is None) or (user_email is None):
            abort(400)

        user_password = generate_password_hash(body.get('password'), method='sha256')
        user = Teacher(first_name=user_first_name, last_name=user_last_name,
                    email=user_email, password=user_password, phone=user_phone,
                    type='teacher')
        if user_university_id is not None:
            user = Student(first_name=user_first_name, last_name=user_last_name,
                           email=user_email, password=user_password, phone=user_phone, university_id=user_university_id,
                           type='student')

        user.insert()
        # generate the auth token
        auth_token = encode_auth_token(app.config.get('SECRET_KEY'), permission=user.type, user_id=user.id)

        return jsonify({
            'success': True,
            'message': 'User has been created',
            'auth_token': auth_token
        })

    else:
        responseObject = {
            'success': False,
            'message': 'User already exists. Please Log in.',
        }
        return make_response(jsonify(responseObject)), 401


@app.route('/login', methods=['POST'])
def loginUser():
    # get the post data
    post_data = request.get_json()
    try:
        # fetch the user data
        user = User.query.filter_by(
            email=post_data.get('email')
        ).first()
        if user and check_password_hash(user.password, post_data.get('password')):
            auth_token = encode_auth_token(app.config.get('SECRET_KEY'), permission=user.type, user_id=user.id)
            if auth_token:
                responseObject = {
                    'success': True,
                    'message': 'Successfully logged in.',
                    'auth_token': auth_token
                }
                return make_response(jsonify(responseObject)), 200
        else:
            abort(404)
    except:
        abort(500)


# @app.route('/users/logout', methods=['POST'])
# def logoutUser():
#     # get auth token
#     auth_header = request.headers.get('Authorization')
#     print(auth_header)
#     if auth_header:
#         auth_token = auth_header.split(" ")[1]
#     else:
#         auth_token = ''
#     print(auth_token)
#     if auth_token:
#         resp = decode_auth_token(app.config.get('SECRET_KEY'), auth_token)
#         if not isinstance(resp, str):
#             # mark the token as blacklisted
#             blacklist_token = BlacklistToken(token=auth_token)
#             try:
#                 # insert the token
#                 blacklist_token.insert()
#                 responseObject = {
#                     'success': True,
#                     'message': 'Successfully logged out.'
#                 }
#                 return make_response(jsonify(responseObject)), 200
#             except Exception as e:
#                 responseObject = {
#                     'success': False,
#                     'message': e
#                 }
#                 return make_response(jsonify(responseObject)), 200
#         else:
#             responseObject = {
#                 'success': False,
#                 'message': resp
#             }
#             return make_response(jsonify(responseObject)), 401
#     else:
#         responseObject = {
#             'success': False,
#             'message': 'Provide a valid auth token.'
#         }
#         return make_response(jsonify(responseObject)), 403

@app.route('/courses/generate_attendance', methods=['POST'])
@requires_auth('teacher')
def attendance_generation(payload):
    post_data = request.get_json()
    try:
        course = Course.query.filter_by(id=post_data.get('course_id')).first()
        if not course:
            abort(404)

        attendance_time_in_minutes = post_data.get('time_in_minutes')
        attendance_token = generate_attendance_code(course.id, attendance_time_in_minutes, app.config.get('SECRET_KEY'))
        if attendance_token:
            responseObject = {
                'success': True,
                'message': 'Successfully generated code',
                'attendance_token': attendance_token
            }
            return make_response(jsonify(responseObject)), 200
    except:
        abort(500)


@app.route('/courses/new', methods=['POST'])
@requires_auth('teacher')
def add_course(payload):
    body = request.get_json()
    course_name = body.get('course_name')
    course_code = body.get('course_code')
    course_grade = body.get('course_grade')
    course = Course.query.filter_by(code=course_code).first()
    if course:
        abort(409)
    try:
        new_course = Course(code=course_code, name=course_name, grade=course_grade)
        new_course.teacher_id = payload.get('id')
        new_course.insert()
        return jsonify({
            'success': True,
            'message': 'Course has been created',
            'course_id': new_course.id,
            'teacher_id': new_course.teacher_id
        })

    except:
        abort(500)


@app.route('/students/attend_class', methods=['POST'])
@requires_auth('student')
def attend_class(payload):
    body = request.get_json()

    course_id = body.get("course_id")
    attendance_token_student = body.get("attendance_token")
    attendance_time_student = body.get("start_time")
    
    student_university_id = body.get("university_id")

    student = Student.query.filter_by(university_id=student_university_id).first()
    course = Course.query.filter_by(id=course_id).first()
    if not student or not course:
        abort(404)
    
    resp = verify_attendance_code(secret_key=app.config.get('SECRET_KEY'), attendance_token=attendance_token_student)
    if not isinstance(resp, str):
        # Check if the student has registered his attendance before
        attendance = Attendance.query.filter_by(attendance_token=attendance_token_student, student_id=student.id).first()
        if attendance:
            return make_response(jsonify({
                "success": False,
                "message": "You have registered your attendance before",
                "can_attends": False
            })), 400
        # mark the token as blacklisted
        #blacklist_token = BlacklistToken(token=attendance_token_student)
        try:
            """
                1- Mark the student as attended
                2- Insert his token to blacklist
            """
            # 1- Mark the student as attended
            new_attendance = Attendance(attendance_time=datetime.datetime.strptime(attendance_time_student, '%Y-%m-%d %H:%M:%S.%f'), attendance_token=attendance_token_student)
            new_attendance.course = course
            student.attendances.append(new_attendance)
            new_attendance.insert()
            # db.session.commit()
            # 2- insert the token
            #blacklist_token.insert()
            responseObject = {
                'success': True,
                'message': 'Successfully marked attendance',
            }
            return make_response(jsonify(responseObject)), 200
        except Exception as e:
            responseObject = {
                'success': False,
                'message': e
            }
            return make_response(jsonify(responseObject)), 200
    else:
        responseObject = {
            'success': False,
            'message': resp
        }
        return make_response(jsonify(responseObject)), 401
        

@app.route('/courses/add_students', methods=['POST'])
@requires_auth('teacher')
def add_students(payload):
    body = request.get_json()
    course_id = body.get('course_id')
    students_list = body.get('students')
    students_university_ids = list(map(lambda x: x['university_id'], students_list))
    
    course = Course.query.filter_by(id=course_id).first()

    if not course:
        abort(404)
    
    for s in students_university_ids:
        student = Student.query.filter_by(university_id=s).first()
        if not student:
            abort(404)
        enroll = Enrollement()
        enroll.course = course
        student.courses.append(enroll)
        student.update()
    
    return make_response(jsonify({
        "success": True,
        "message": "Students added successfully to the course"
    })), 200

# Error Handling
@app.errorhandler(422)
def unprocessable(error):
    return jsonify({
        "success": False,
        "error": 422,
        "message": "unprocessable"
    }), 422


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": 404,
        "message": "resource not found"
    }), 404


@app.errorhandler(401)
def unauthorized(error):
    return jsonify({
        "success": False,
        "error": 401,
        "message": 'Unauthorized'
    }), 401


@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({
        "success": False,
        "error": 500,
        "message": 'Internal Server Error'
    }), 500


@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        "success": False,
        "error": 400,
        "message": 'Bad Request'
    }), 400


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "success": False,
        "error": 405,
        "message": 'Method Not Allowed'
    }), 405

@app.errorhandler(409)
def resource_exist(error):
    return jsonify({
        "success": False,
        "error": 409,
        "message": "Resource Already Exists"
    })
if __name__ == '__main__':
    app.run()
