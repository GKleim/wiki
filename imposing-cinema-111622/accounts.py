from handler import Handler
from utils import *
from entities import User

class SignUp(Handler):
	def render_signup(self, username='', email='', username_error='',
						password_error='', verify_error='', email_error=''):
		self.render('signup.html', username=username, email=email,
						username_error=username_error, password_error=password_error,
						verify_error=verify_error, email_error=email_error)

	def get(self):
		self.render_signup()

	def post(self):
		have_error = False

		self.username = self.request.get('username')
		self.password = self.request.get('password')
		self.verify = self.request.get('verify')
		self.email = self.request.get('email')

		params = dict(username=self.username, email=self.email)

		if not valid_username(self.username):
			have_error = True
			params['username_error'] = 'please enter a valid username'
		if not self.password:
			have_error = True
			params['password_error'] = 'please enter a password'
		elif not valid_password(self.password,self.verify):
			have_error = True
			params['verify_error'] = 'passwords did not match'
		if self.email and not valid_email(self.email):
			have_error = True
			params['email_error'] = 'please enter a valid email'

		if have_error:
			self.render_signup(**params)
		else:
			self.done(**params)
		
	def done(self, *a, **kw):
		raise NotImplementedError


class Register(SignUp):
	def done(self, *a, **kw):
		u = User.by_name(self.username)
		if u:
			msg = 'user is already registered'
			self.render_signup(username_error=msg, **kw)
		else:
			u = User.register(self.username, self.password, self.email)
			u.put()

			self.login(u)
			self.redirect('/blog/welcome')


class Login(Handler):
	def render_login(self, username='', login_error=''):
		self.render('login.html', username=username, login_error=login_error)

	def get(self):
		self.render_login()

	def post(self):
		username = self.request.get('username')
		password = self.request.get('password')

		user = User.login(username, password)

		if user:
			self.login(user)
			self.redirect('/blog/welcome')
		else:
			login_error = 'invalid login'
			self.render_login(username=username, login_error=login_error)


class Welcome(Handler):
	def get(self):
		if self.user:
			self.render("welcome.html", username=self.user.username)
		else:
			self.redirect('/blog/signup')


class Logout(Handler):
	def get(self):
		self.logout()
		self.redirect('/blog/signup')