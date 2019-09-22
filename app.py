from flask import Flask
from flask_compress import Compress
from flask_caching import Cache
import pymongo
import pprint
from bson.json_util import dumps
import json
from bson import json_util
from flask import jsonify
import collections
import math

app = Flask(__name__)
Compress(app)
cache = Cache(config={'CACHE_TYPE': 'simple'})
cache.init_app(app)

client = pymongo.MongoClient('mongodb+srv://prodigal_be_test_01:prodigaltech@test-01-ateon.mongodb.net/sample_training')
db = client['sample_training']

@app.route("/")
def hello():
	return "Welcome to Python Flask!"

@app.route("/students", methods=['GET'])
@cache.cached(500,key_prefix='name')
def students():
	obj = list(db['students'].find())
	return jsonify(obj)

@app.route("/student/<student_id>/classes", methods=['GET'])
def student_classes(student_id):
	records = db['grades'].find({'student_id': int(student_id)})
	student = list(db['students'].find({'_id': int(student_id)}, {'name': 1, '_id': 0}))[0]['name']
	classes = []
	for record in records:
		classes.append({'class_id': record['class_id']})

	obj = {'student_id': int(student_id), 'student_name': student, 'classes': classes}
	return jsonify(obj)

@app.route("/student/<student_id>/performance", methods=['GET'])
def student_performance(student_id):
	records = db['grades'].find({'student_id': int(student_id)})
	performance = []
	for record in records:
		performance.append({'class_id': record['class_id'], 'total_marks': math.floor(sum([pair['score'] for pair in record['scores']]))})

	student = list(db['students'].find({'_id': int(student_id)}, {'name': 1, '_id': 0}))[0]['name']
	obj = {'student_id': int(student_id), 'student_name': student, 'classes': performance}
	return jsonify(obj)

@app.route("/classes", methods=['GET'])
@cache.cached(500,key_prefix='class_id')
def classes():
	obj = list(db['grades'].find({}, {'scores': 0, '_id': 0, 'student_id': 0}))
	return jsonify(obj)

@app.route("/class/<class_id>/students", methods=['GET'])
def class_students(class_id):
	class_detail = db['grades'].find({'class_id': int(class_id)}, {'scores': 0, '_id': 0, 'class_id': 0})
	students = []
	for student in class_detail:
		std = list(db['students'].find({'_id': student['student_id']}, {'name': 1, '_id': 0}))[0]['name']
		students.append({'student_id': student['student_id'], 'student_name': std})
	obj = {'class_id': class_id, 'students': students}
	return jsonify(obj)

@app.route("/class/<class_id>/performance", methods=['GET'])
def class_performance(class_id):
	class_detail = db['grades'].find({'class_id': int(class_id)}, {'_id': 0, 'class_id': 0})
	students = []
	for student in class_detail:
		std = list(db['students'].find({'_id': student['student_id']}, {'name': 1, '_id': 0}))[0]['name']
		performance = math.floor(sum([pair['score'] for pair in student['scores']]))
		students.append({'student_id': student['student_id'], 'student_name': std, 'total_marks': performance})
	obj = {'class_id': class_id, 'students': students}
	return jsonify(obj)

@app.route("/class/<class_id>/final-grade-sheet", methods=['GET'])
def class_gradesheet(class_id):
	class_detail = db['grades'].find({'class_id': int(class_id)}, {'_id': 0, 'class_id': 0})
	total_count = len(list(class_detail))
	A = math.ceil(total_count / 12)
	B = math.ceil((total_count - A) / 6)
	C = math.ceil((total_count - (A + B)) / 4)

	total_marks = []
	for score in class_detail.rewind():
		total_marks.append((score['student_id'], math.floor(sum([pair['score'] for pair in score['scores']]))))

	sorted_data = sorted(total_marks, key=lambda x: x[1], reverse=True)
	A_marks = sorted_data[A-1][1]
	B_marks = sorted_data[A+B-1][1]
	C_marks = sorted_data[A+B+C-1][1]

	students = []
	for student in class_detail.rewind():
		std = list(db['students'].find({'_id': student['student_id']}, {'name': 1, '_id': 0}))[0]['name']
		marks = math.floor(sum([pair['score'] for pair in student['scores']]))

		if(marks>=A_marks):
			grade = 'A'
		elif(marks>=B_marks and marks < A_marks):
			grade = 'B'
		elif(marks>=C_marks and marks < B_marks):
			grade = 'C'
		else:
			grade = 'D'
		students.append({'student_id': student['student_id'], 'student_name': std, 'details': student['scores'], 'grade':grade})

	obj = {'class_id': class_id, 'students': students}
	return jsonify(obj)

@app.route("/class/<class_id>/student/<student_id>", methods=['GET'])
def class_student(class_id, student_id):
	try:
		class_detail = list(db['grades'].find({'$and': [{'class_id': int(class_id), 'student_id': int(student_id)}]}, {'student_id': 0, '_id': 0, 'class_id': 0}))[0]['scores']
		std = list(db['students'].find({'_id': int(student_id)}, {'name': 1, '_id': 0}))[0]['name']
		obj = {'class_id': int(class_id), 'student_id': int(student_id), 'student_name': std, 'marks': class_detail}
	except Exception:
		return json.dumps({"error": 'No Data Found. Try some other IDs.'}), 500
	return jsonify(obj)
