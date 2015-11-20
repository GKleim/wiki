# accounts.py
# This .py file contains handlers for user account features
# This file should only contain user accounts handlers and related functions (?)

from handler import Handler
from utils import *
from entities import User
from webapp2 import uri_for

# The SignUp class is the base class for register/sign up classes.
# The SignUp handler acts as the signup form input validation
class SignUp(Handler):
	# The render_signup function simplifies the html render call
	def render_signup(self, username='', email='', username_error='',
						password_error='', verify_error='', email_error=''):
		self.render('signup.html', username=username, email=email,
						username_error=username_error, password_error=password_error,
						verify_error=verify_error, email_error=email_error)

	# GET: renders sgnup html
	def get(self):
		self.render_signup()

	# POST:
	def post(self):
		# have_error is True if any of the inputs do not pass validation
		have_error = False

		# assign form data to instance variables
		self.username = self.request.get('username')
		self.password = self.request.get('password')
		self.verify = self.request.get('verify')
		self.email = self.request.get('email')

		# initialize dictionary of inputs to html render function
		params = dict(username=self.username, email=self.email)

		# checks for a valid username by comparing to a RegEx
		if not valid_username(self.username):
			have_error = True
			params['username_error'] = 'please enter a valid username'
		# checks for absence of a password
		if not self.password:
			have_error = True
			params['password_error'] = 'please enter a password'
		# checks for compliant password (password and verify password fields)
		elif not valid_password(self.password,self.verify):
			have_error = True
			params['verify_error'] = 'passwords did not match'
		# checks for valid email by comparing to a RegEx if an email was entered
		if self.email and not valid_email(self.email):
			have_error = True
			params['email_error'] = 'please enter a valid email'

		# if input does not pass validation, render html with error messages
		if have_error:
			self.render_signup(**params)
		# if input passes validation, take the action of the done function
		else:
			self.done(**params)
	
	# The done function is meant to be written over by child class to modify the action taken
	# after a POST request
	def done(self, *a, **kw):
		raise NotImplementedError


# The Register class inherits from SignUp and handles user registration
class Register(SignUp):
	# The done function overwrites the done function of the SignUp parent class
	def done(self, *a, **kw):

		# query User entities for the submitted username
		u = User.by_name(self.username)

		# throw an error message if the username is already taken
		if u:
			msg = 'user is already registered'
			self.render_signup(username_error=msg, **kw)

		# register user if username is not taken
		else:
			# call the register classmethod on User to create a new User in the db
			u = User.register(self.username, self.password, self.email)
			u.put()

			# automatically log the user in and redirect to the welcome page
			self.login(u)
			self.redirect(uri_for('welcome'))


# The Login class handles requests to the user login page
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
			self.redirect(uri_for('welcome'))
		else:
			login_error = 'invalid login'
			self.render_login(username=username, login_error=login_error)


# The Welcome class renders html for welcome page requests
class Welcome(Handler):
	def get(self):
		# self.user is inherited from the Handler class
		if self.user:
			self.render("welcome.html", username=self.user.username)
		else:
			self.redirect(uri_for('signup'))

# The Logout class logs the user out
class Logout(Handler):
	def get(self):
		# self.logout() is an instance method inherited from Handler class
		self.logout()
		self.redirect('/_signup')