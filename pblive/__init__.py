#    PBLive
#    Copyright © 2017  RunasSudo (Yingtong Li)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import flask
import flask_socketio

import pblive.data

import os
import random
import sys
import yaml

app = flask.Flask('pblive')
app.jinja_env.globals['data'] = pblive.data

socketio = flask_socketio.SocketIO(app)

# Load session data
for f in os.listdir('data'):
	if f.endswith('.yaml'):
		session_name = f[:-5]
		with open(os.path.join('data', f)) as fh:
			session = yaml.load(fh)
			session['name'] = session_name
			
			session['colours'] = [(1, '#f44336'), (2, '#e91e63'), (3, '#9c27b0'), (4, '#673ab7'), (5, '#3f51b5'), (6, '#2196f3'), (7, '#03a9f4'), (8, '#00bcd4'), (9, '#009688'), (10, '#4caf50'), (11, '#8bc34a'), (12, '#cddc39'), (13, '#ffeb3b'), (14, '#ffc107'), (15, '#ff9800'), (16, '#ff5722'), (17, '#795548'), (18, '#9e9e9e'), (19, '#607d8b')]
			session['question_num'] = 0
			
			pblive.data.sessions[session_name] = session

@app.route('/')
def index():
	return flask.render_template('index.html')

@app.route('/admin')
def admin():
	return flask.render_template('admin.html')

@app.route('/session/<session_name>')
def session(session_name):
	return flask.render_template('session.html', session=pblive.data.sessions[session_name])

@app.route('/image/<location>')
def image(location):
	# TODO: Relative path
	return flask.send_from_directory('/home/runassudo/Documents/pblive/data/img', location)

@app.route('/admin/session/<session_name>')
def admin_session(session_name):
	return flask.render_template('admin_session.html', session=pblive.data.sessions[session_name])

@socketio.on('join')
def socket_join(session_name):
	app.logger.debug('New client {} connected'.format(flask.request.sid))
	
	user = {'sid': flask.request.sid, 'session_name': session_name, 'answers': {}}
	session = pblive.data.sessions[session_name]
	pblive.data.users[flask.request.sid] = user
	
	flask_socketio.join_room(session_name)
	
	# Send initial colour picker
	flask_socketio.emit('update', flask.render_template('colour_picker.html', session=session), room=flask.request.sid)

def render_question(user, session, question_num):
	if session['questions'][question_num]['type'] == 'mcq':
		template = 'question_mcq.html'
	elif session['questions'][question_num]['type'] == 'random':
		template = 'question_random.html'
	elif session['questions'][question_num]['type'] == 'draw':
		template = 'question_draw.html'
	
	return flask.render_template(template, session=session, user=user, question_num=session['question_num'])

def render_question_admin(session, question_num):
	if session['questions'][question_num]['type'] == 'mcq':
		template = 'question_mcq_admin.html'
	elif session['questions'][question_num]['type'] == 'random':
		template = 'question_random_admin.html'
	elif session['questions'][question_num]['type'] == 'draw':
		template = 'question_draw_admin.html'
	
	return flask.render_template(template, session=session, question_num=session['question_num'])

@socketio.on('join_admin')
def socket_join(session_name):
	app.logger.debug('New admin {} connected'.format(flask.request.sid))
	
	user = {'sid': flask.request.sid, 'session_name': session_name}
	session = pblive.data.sessions[session_name]
	pblive.data.admins[flask.request.sid] = user
	
	# Send initial screen
	flask_socketio.emit('update', render_question_admin(session, session['question_num']), room=flask.request.sid)

@socketio.on('disconnect')
def socket_disconnect():
	app.logger.debug('Client {} disconnected'.format(flask.request.sid))
	
	if flask.request.sid in pblive.data.users:
		user = pblive.data.users[flask.request.sid]
		session = pblive.data.sessions[user['session_name']]
		
		flask_socketio.leave_room(session['name'])
		
		# Release the colour if it's being held
		if 'colour' in user:
			session['colours'].append(user['colour'])
			
			# Relay change
			for _, other_user in pblive.data.users.items():
				if other_user != user and 'colour' not in other_user and other_user['session_name'] == session['name']:
					flask_socketio.emit('update', flask.render_template('colour_picker.html', session=session), room=other_user['sid'])
		
		del pblive.data.users[flask.request.sid]

@socketio.on('register')
def socket_register(colour_id, colour_name):
	user = pblive.data.users[flask.request.sid]
	session = pblive.data.sessions[user['session_name']]
	
	flask_socketio.emit('update', render_question(user, session, session['question_num']), room=user['sid'])
	
	if 'colour' not in user and (colour_id, colour_name) in session['colours']:
		user['colour'] = (colour_id, colour_name)
		session['colours'].remove((colour_id, colour_name))
		
		# Relay change
		for _, other_user in pblive.data.users.items():
			if other_user != user and 'colour' not in other_user and other_user['session_name'] == session['name']:
				flask_socketio.emit('update', flask.render_template('colour_picker.html', session=session), room=other_user['sid'])

@socketio.on('answer')
def socket_answer(question_num, answer):
	user = pblive.data.users[flask.request.sid]
	session = pblive.data.sessions[user['session_name']]
	
	if question_num == session['question_num']:
		user['answers'][question_num] = answer
		
		if session['questions'][session['question_num']]['type'] != 'draw':
			flask_socketio.emit('update', render_question(user, session, session['question_num']), room=user['sid'])
		
		# Relay change
		for _, admin in pblive.data.admins.items():
			flask_socketio.emit('update', render_question_admin(session, session['question_num']), room=admin['sid'])

@socketio.on('reveal_answers')
def socket_reveal_answers(question_num):
	user = pblive.data.admins[flask.request.sid]
	session = pblive.data.sessions[user['session_name']]
	
	session['questions'][question_num]['revealed'] = True
	
	flask_socketio.emit('update', render_question_admin(session, session['question_num']), room=flask.request.sid)

@socketio.on('goto_question')
def socket_goto_question(question_num):
	user = pblive.data.admins[flask.request.sid]
	session = pblive.data.sessions[user['session_name']]
	
	session['question_num'] = question_num
	
	# Do work for some questions
	if session['questions'][question_num]['type'] == 'random':
		session['questions'][question_num]['answerer'] = random.choice([user for _, user in pblive.data.users.items() if user['session_name'] == session['name'] and 'colour' in user])
	
	# Relay change
	for _, user in pblive.data.users.items():
		if user['session_name'] == session['name'] and 'colour' in user:
			flask_socketio.emit('update', render_question(user, session, session['question_num']), room=user['sid'])
	for _, admin in pblive.data.admins.items():
			flask_socketio.emit('update', render_question_admin(session, session['question_num']), room=admin['sid'])

@socketio.on('pass_question')
def socket_pass_question():
	user = pblive.data.admins[flask.request.sid] if flask.request.sid in pblive.data.admins else pblive.data.users[flask.request.sid]
	session = pblive.data.sessions[user['session_name']]
	
	if session['questions'][session['question_num']]['type'] == 'random':
		# Re-randomise answerer
		session['questions'][session['question_num']]['answerer'] = random.choice([user for _, user in pblive.data.users.items() if user['session_name'] == session['name'] and 'colour' in user])
		
		# Relay change
		for _, user in pblive.data.users.items():
			if user['session_name'] == session['name'] and 'colour' in user:
				flask_socketio.emit('update', render_question(user, session, session['question_num']), room=user['sid'])
		for _, admin in pblive.data.admins.items():
				flask_socketio.emit('update', render_question_admin(session, session['question_num']), room=admin['sid'])
