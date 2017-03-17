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

sessions = {}
users = {}
admins = {}

class Session:
	def __init__(self, name=None, title=None, questions=None, colours=None, question_num=0):
		if questions is None:
			questions = []
		if colours is None:
			colours = [(1, '#f44336'), (2, '#e91e63'), (3, '#9c27b0'), (4, '#673ab7'), (5, '#3f51b5'), (6, '#2196f3'), (7, '#03a9f4'), (8, '#00bcd4'), (9, '#009688'), (10, '#4caf50'), (11, '#8bc34a'), (12, '#cddc39'), (13, '#ffeb3b'), (14, '#ffc107'), (15, '#ff9800'), (16, '#ff5722'), (17, '#795548'), (18, '#9e9e9e'), (19, '#607d8b')]
		
		self.name = name
		self.title = title
		self.questions = questions
		self.colours = colours
		self.question_num = question_num
	
	@classmethod
	def from_dict(cls, obj, name):
		return cls(name=name, title=obj['title'], questions=[Question.from_dict(x) for x in obj['questions']])

class Question:
	def __init__(self, prompt=None, image=None, answers=None, revealed=False):
		if answers is None:
			answers = []
		
		self.prompt = prompt
		self.image = image
		self.answers = answers
		self.revealed = False
	
	@staticmethod
	def from_dict(obj):
		question_types = {
			'mcq': MCQQuestion,
			'draw': DrawQuestion,
			'random': RandomQuestion
		}
		question = question_types[obj['type']]()
		question.load_dict(obj)
		return question
	
	def load_dict(self, obj):
		if 'prompt' in obj:
			self.prompt = obj['prompt']
		if 'image' in obj:
			self.image = obj['image']
		if 'answers' in obj:
			self.answers = obj['answers']

class MCQQuestion(Question):
	template = 'question_mcq.html'
	template_admin = 'question_mcq_admin.html'

class DrawQuestion(Question):
	template = 'question_draw.html'
	template_admin = 'question_draw_admin.html'

class RandomQuestion(Question):
	template = 'question_random.html'
	template_admin = 'question_random_admin.html'
	
	def __init__(self):
		self.answerer = None

class User:
	def __init__(self, sid=None, session=None, answers=None, colour=None):
		if answers is None:
			answers = {}
		
		self.sid = sid
		self.session = session
		self.answers = answers
		self.colour = colour

class Admin(User):
	pass

def responses_for_question(session, question_num):
	return len([user for _, user in users.items() if user.session == session and question_num in user.answers])
