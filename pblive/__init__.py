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

import eventlet
import flask
import flask_socketio

import pblive.data

import os
import random
import socket
import sys
import yaml

eventlet.monkey_patch()

app = flask.Flask('pblive')
app.jinja_env.globals['data'] = pblive.data

socketio = flask_socketio.SocketIO(app)

# Get server IP address
tmp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
tmp_socket.connect(('8.8.8.8', 0)) # Connecting to a UDP socket sends no packets
pblive.data.server_ip = tmp_socket.getsockname()[0]
tmp_socket.close()

# Load session data
for f in os.listdir('data'):
	if f.endswith('.yaml') and not f.startswith('.'):
		session_name = f[:-5]
		with open(os.path.join('data', f)) as fh:
			pblive.data.sessions[session_name] = pblive.data.Session.from_dict(yaml.load(fh), session_name)

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
	user = pblive.data.User(sid=flask.request.sid, session=session)
	pblive.data.users[flask.request.sid] = user
	
	# Send initial colour picker
	flask_socketio.emit('update', flask.render_template('colour_picker.html', session=session), room=flask.request.sid)
	flask_socketio.emit('update_left', render_sidebar(user, session), room=flask.request.sid)

def render_question(user, session, question_num):
	return flask.render_template(session.questions[question_num].template, session=session, user=user, question_num=session.question_num)

def render_question_admin(session, question_num):
	return flask.render_template(session.questions[question_num].template_admin, session=session, question_num=session.question_num)

def render_sidebar(user, session):
	return flask.render_template('users.html', session=session, user=user)

@socketio.on('join_admin')
def socket_join(session_name):
	app.logger.debug('New admin {} connected'.format(flask.request.sid))
	
	session = pblive.data.sessions[session_name]
	user = pblive.data.Admin(sid=flask.request.sid, session=session)
	pblive.data.admins_lock.acquire()
	pblive.data.admins[flask.request.sid] = user
	pblive.data.admins_lock.release()
	
	# Send initial screen
	flask_socketio.emit('update', render_question_admin(session, session.question_num), room=flask.request.sid)
	flask_socketio.emit('update_left', render_sidebar(user, session), room=flask.request.sid)

@socketio.on('disconnect')
def socket_disconnect():
	app.logger.debug('Client {} disconnected'.format(flask.request.sid))
	
	if flask.request.sid in pblive.data.users:
		user = pblive.data.users[flask.request.sid]
		
		# Release the colour if it's being held
		if user.colour:
			user.session.colours.append(user.colour)
			
			# Relay change
			for _, other_user in pblive.data.iterate_users():
				if other_user != user and other_user.session == user.session:
					flask_socketio.emit('update_left', render_sidebar(other_user, user.session), room=other_user.sid)
					if not other_user.colour:
						flask_socketio.emit('update', flask.render_template('colour_picker.html', session=user.session), room=other_user.sid)
			for _, admin in pblive.data.iterate_admins():
				if admin.session == user.session:
					flask_socketio.emit('update_left', render_sidebar(admin, user.session), room=admin.sid)
		
		pblive.data.users_lock.acquire()
		del pblive.data.users[flask.request.sid]
		pblive.data.users_lock.release()

@socketio.on('register')
def socket_register(colour_id, colour_name):
	user = pblive.data.users[flask.request.sid]
	
	if not user.colour and (colour_id, colour_name) in user.session.colours:
		user.colour = (colour_id, colour_name)
		user.session.colours.remove(user.colour)
		
		# Relay change
		for _, other_user in pblive.data.iterate_users():
			if other_user != user and other_user.session == user.session:
				flask_socketio.emit('update_left', render_sidebar(other_user, user.session), room=other_user.sid)
				if not other_user.colour:
					flask_socketio.emit('update', flask.render_template('colour_picker.html', session=user.session), room=other_user.sid)
		for _, admin in pblive.data.iterate_admins():
			if admin.session == user.session:
				flask_socketio.emit('update_left', render_sidebar(admin, user.session), room=admin.sid)
	
	flask_socketio.emit('update', render_question(user, user.session, user.session.question_num), room=user.sid)
	flask_socketio.emit('update_left', render_sidebar(user, user.session), room=user.sid)

@socketio.on('answer')
def socket_answer(question_num, answer):
	user = pblive.data.users[flask.request.sid]
	
	if question_num == user.session.question_num:
		if isinstance(user.session.questions[user.session.question_num], pblive.data.SpeedQuestion):
			if question_num in user.answers:
				# Only one shot!
				return
		
		user.answers[question_num] = answer
		
		if isinstance(user.session.questions[user.session.question_num], pblive.data.MCQQuestion):
			flask_socketio.emit('update', render_question(user, user.session, user.session.question_num), room=user.sid)
		
		# Hurry!
		if isinstance(user.session.questions[user.session.question_num], pblive.data.SpeedQuestion):
			if user.session.questions[user.session.question_num].timer_thread is None:
				user.session.questions[user.session.question_num].timer_thread = pblive.data.SpeedQuestionTimerThread(flask.copy_current_request_context(do_goto_question), user.session, user.session.question_num + 1)
				user.session.questions[user.session.question_num].timer_thread.start()
		
		# Relay change
		for _, other_user in pblive.data.iterate_users():
			if other_user.session == user.session:
				flask_socketio.emit('update_left', render_sidebar(other_user, user.session), room=other_user.sid)
				if isinstance(user.session.questions[user.session.question_num], pblive.data.SpeedQuestion):
					flask_socketio.emit('update', render_question(other_user, user.session, user.session.question_num), room=other_user.sid)
		for _, admin in pblive.data.iterate_admins():
			if admin.session == user.session:
				flask_socketio.emit('update', render_question_admin(user.session, user.session.question_num), room=admin.sid)
				flask_socketio.emit('update_left', render_sidebar(admin, user.session), room=admin.sid)

@socketio.on('reveal_answers')
def socket_reveal_answers(question_num):
	user = pblive.data.admins[flask.request.sid]
	
	user.session.questions[question_num].revealed = True
	
	flask_socketio.emit('update', render_question_admin(user.session, user.session.question_num), room=flask.request.sid)

def do_goto_question(session, question_num):
	# Cleanup old question
	if isinstance(session.questions[session.question_num], pblive.data.SpeedQuestion):
		if session.questions[session.question_num].timer_thread is not None:
			session.questions[session.question_num].timer_thread.stop()
	
	session.question_num = question_num
	
	# Do work for some questions
	if isinstance(session.questions[question_num], pblive.data.RandomQuestion):
		session.questions[question_num].answerer = random.choice([other_user for _, other_user in pblive.data.users.items() if other_user.session == session and other_user.colour])
	
	# Relay change
	for _, other_user in pblive.data.iterate_users():
		if other_user.session == session and other_user.colour:
			flask_socketio.emit('update', render_question(other_user, session, session.question_num), room=other_user.sid)
			flask_socketio.emit('update_left', render_sidebar(other_user, session), room=other_user.sid)
	for _, admin in pblive.data.iterate_admins():
		if admin.session == session:
			flask_socketio.emit('update', render_question_admin(session, session.question_num), room=admin.sid)
			flask_socketio.emit('update_left', render_sidebar(admin, session), room=admin.sid)

@socketio.on('goto_question')
def socket_goto_question(question_num):
	user = pblive.data.admins[flask.request.sid]
	
	do_goto_question(user.session, question_num)

@socketio.on('pass_question')
def socket_pass_question():
	user = pblive.data.admins[flask.request.sid] if flask.request.sid in pblive.data.admins else pblive.data.users[flask.request.sid]
	
	if isinstance(user.session.questions[user.session.question_num], pblive.data.RandomQuestion):
		# Re-randomise answerer
		user.session.questions[user.session.question_num].answerer = random.choice([other_user for _, other_user in pblive.data.users.items() if other_user.session == user.session and other_user.colour])
		
		# Relay change
		for _, other_user in pblive.data.iterate_users():
			if other_user.session == user.session and other_user.colour:
				flask_socketio.emit('update', render_question(other_user, other_user.session, other_user.session.question_num), room=other_user.sid)
				flask_socketio.emit('update_left', render_sidebar(other_user, user.session), room=other_user.sid)
		for _, admin in pblive.data.iterate_admins():
			if admin.session == user.session:
				flask_socketio.emit('update', render_question_admin(admin.session, admin.session.question_num), room=admin.sid)
				flask_socketio.emit('update_left', render_sidebar(admin, user.session), room=admin.sid)

# Start server
if __name__ == '__main__':
	socketio.run(app, host='0.0.0.0')
