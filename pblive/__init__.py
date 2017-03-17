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
			pblive.data.sessions[session_name] = data.Session.from_dict(yaml.load(fh), session_name)

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

@app.route('/debug')
def debug():
	assert app.debug == False

@socketio.on('join')
def socket_join(session_name):
	app.logger.debug('New client {} connected'.format(flask.request.sid))
	
	session = pblive.data.sessions[session_name]
	user = data.User(sid=flask.request.sid, session=session)
	pblive.data.users[flask.request.sid] = user
	
	# Send initial colour picker
	flask_socketio.emit('update', flask.render_template('colour_picker.html', session=session), room=flask.request.sid)

def render_question(user, session, question_num):
	return flask.render_template(session.questions[question_num].template, session=session, user=user, question_num=session.question_num)

def render_question_admin(session, question_num):
	return flask.render_template(session.questions[question_num].template_admin, session=session, question_num=session.question_num)

@socketio.on('join_admin')
def socket_join(session_name):
	app.logger.debug('New admin {} connected'.format(flask.request.sid))
	
	session = pblive.data.sessions[session_name]
	user = pblive.data.Admin(sid=flask.request.sid, session=session)
	pblive.data.admins[flask.request.sid] = user
	
	# Send initial screen
	flask_socketio.emit('update', render_question_admin(session, session.question_num), room=flask.request.sid)

@socketio.on('disconnect')
def socket_disconnect():
	app.logger.debug('Client {} disconnected'.format(flask.request.sid))
	
	if flask.request.sid in pblive.data.users:
		user = pblive.data.users[flask.request.sid]
		
		# Release the colour if it's being held
		if user.colour:
			user.session.colours.append(user.colour)
			
			# Relay change
			for _, other_user in pblive.data.users.items():
				if other_user != user and 'colour' not in other_user and other_user.session == user.session:
					flask_socketio.emit('update', flask.render_template('colour_picker.html', session=user.session), room=other_user.sid)
		
		del pblive.data.users[flask.request.sid]

@socketio.on('register')
def socket_register(colour_id, colour_name):
	user = pblive.data.users[flask.request.sid]
	flask_socketio.emit('update', render_question(user, user.session, user.session.question_num), room=user.sid)
	
	if not user.colour and (colour_id, colour_name) in user.session.colours:
		user.colour = (colour_id, colour_name)
		user.session.colours.remove(user.colour)
		
		# Relay change
		for _, other_user in pblive.data.users.items():
			if other_user != user and not other_user.colour and other_user.session == user.session:
				flask_socketio.emit('update', flask.render_template('colour_picker.html', session=user.session), room=other_user.sid)

@socketio.on('answer')
def socket_answer(question_num, answer):
	user = pblive.data.users[flask.request.sid]
	
	if question_num == user.session.question_num:
		user.answers[question_num] = answer
		
		if not isinstance(user.session.questions[user.session.question_num], pblive.data.DrawQuestion):
			flask_socketio.emit('update', render_question(user, user.session, user.session.question_num), room=user.sid)
		
		# Relay change
		for _, admin in pblive.data.admins.items():
			flask_socketio.emit('update', render_question_admin(user.session, user.session.question_num), room=admin.sid)

@socketio.on('reveal_answers')
def socket_reveal_answers(question_num):
	user = pblive.data.admins[flask.request.sid]
	
	user.session.questions[question_num].revealed = True
	
	flask_socketio.emit('update', render_question_admin(user.session, user.session.question_num), room=flask.request.sid)

@socketio.on('goto_question')
def socket_goto_question(question_num):
	user = pblive.data.admins[flask.request.sid]
	
	user.session.question_num = question_num
	
	# Do work for some questions
	if isinstance(user.session.questions[question_num], pblive.data.RandomQuestion):
		user.session.questions[question_num].answerer = random.choice([other_user for _, other_user in pblive.data.users.items() if other_user.session == user.session and other_user.colour])
	
	# Relay change
	for _, other_user in pblive.data.users.items():
		if other_user.session == user.session and other_user.colour:
			flask_socketio.emit('update', render_question(other_user, other_user.session, other_user.session.question_num), room=other_user.sid)
	for _, admin in pblive.data.admins.items():
			flask_socketio.emit('update', render_question_admin(admin.session, admin.session.question_num), room=admin.sid)

@socketio.on('pass_question')
def socket_pass_question():
	user = pblive.data.admins[flask.request.sid] if flask.request.sid in pblive.data.admins else pblive.data.users[flask.request.sid]
	
	if isinstance(user.session.questions[user.session.question_num], pblive.data.RandomQuestion):
		# Re-randomise answerer
		user.session.questions[user.session.question_num].answerer = random.choice([other_user for _, other_user in pblive.data.users.items() if other_user.session == user.session and other_user.colour])
		
		# Relay change
		for _, other_user in pblive.data.users.items():
			if other_user.session == user.session and other_user.colour:
				flask_socketio.emit('update', render_question(other_user, other_user.session, other_user.session.question_num), room=other_user.sid)
		for _, admin in pblive.data.admins.items():
				flask_socketio.emit('update', render_question_admin(admin.session, admin.session.question_num), room=admin.sid)
