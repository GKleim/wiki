#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2
import os
from google.appengine.ext import db
from google.appengine.api import memcache
from datetime import datetime, timedelta
import hmac
import hashlib
import re
import random
import string
import json
import logging
import time

secret = 'secret'

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
									autoescape = True) #autoescape HTML
USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return USER_RE.match(username)

EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")
def valid_email(email):
    return EMAIL_RE.match(email)

def valid_password(password,verify):
	return password == verify

def hash_str(s):
	return hmac.new(secret,s).hexdigest()

def make_secure_val(s):
	return '%s|%s' % (s, hash_str(s))

def check_secure_val(h):
	val = h.split('|')[0]
	if h == make_secure_val(val):
		return val

def make_salt():
	return ''.join(random.choice(string.letters) for x in xrange(5))

def make_pw_hash(name, pw, salt = None):
	if not salt:
		salt = make_salt()
	h = hashlib.sha256(name+pw+salt).hexdigest()
	return '%s,%s' % (h, salt)

def valid_pw(name, pw, h):
	salt = h.split(',')[1]
	return h == make_pw_hash(name, pw, salt)


class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
    	t = jinja_env.get_template(template)
    	return t.render(params)

    def render(self, template, **kw):
    	login_name = None
    	if self.user:
    		user = self.user
    		login_name = user.username
    	self.write(self.render_str(template, login_name=login_name, **kw))

    def render_json(self, d):
    	json_text = json.dumps(d)
    	self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
    	self.write(json_text)

    def set_secure_cookie(self, name, val):
    	cookie_val = make_secure_val(val)
    	self.response.headers.add_header(
    		'Set-Cookie',
    		'%s=%s; Path=/' % (name, cookie_val)) # can include Expires param

    def read_secure_cookie(self, name):
    	cookie_val = self.request.cookies.get(name)
    	return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
    	self.set_secure_cookie('user_id', str(user.key().id()))   	

    def logout(self):
    	self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    def initialize(self, *a, **kw):
    	webapp2.RequestHandler.initialize(self, *a, **kw)
    	uid = self.read_secure_cookie('user_id')
    	self.user = uid and User.by_id(int(uid))

    	if self.request.url.endswith('.json'):
    		self.format = 'json'
    	else:
    		self.format = 'html'


def blog_key(name = 'default'):
	return db.Key.from_path('blogs', name)
	# This is for adding a parent? I do not use this function in my code

class Post(db.Model):
	subject = db.StringProperty(required = True)
	content = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)
	modified = db.DateTimeProperty(auto_now = True)

	def as_dict(self):
		time_fmt = '%c'
		d = {"subject": self.subject,
	         "content": self.content,
	         "created": self.created.strftime(time_fmt),
	         "modified": self.modified.strftime(time_fmt)}
		return d


def users_key(group = 'default'):
	return db.Key.from_path('users', group)

class User(db.Model):
	username = db.StringProperty(required = True)
	password = db.StringProperty(required = True)
	email = db.StringProperty()
	joined = db.DateTimeProperty(auto_now_add = True)

	@classmethod
	def by_id(cls, uid):
		return cls.get_by_id(uid, parent = users_key())

	@classmethod
	def by_name(cls, username):
		u = cls.all().filter('username =', username).get()
		return u

	@classmethod
	def register(cls, username, password, email = None):
		password = make_pw_hash(username, password)
		return cls(parent = users_key(),
					username = username,
					password = password,
					email = email)

	@classmethod
	def login(cls, username, password):
		u = cls.by_name(username)
		if u and valid_pw(username, password, u.password):
			return u

def top_entries(update = False):
	key = 'top'
	entries = memcache.get(key)
	if entries is None or update:
		print 'DB Query'
		#database query for all posts
		entries = Post.all().ancestor(blog_key()).order("-created").run(limit=10)
		#db is not queried until something is ran on entries. Make a list out of the
		#query to force the query to run. This prevents potentially running the query
		#multiple times in later code
		entries = list(entries)
		memcache.set(key, entries)
		memcache.set("time", datetime.now())
	return entries

def get_entry(entry_id):
	key = '%s' % entry_id
	entry = memcache.get(key)
	if entry is None:
		#database query for post with entry_id
		entry = Post.get_by_id(int(entry_id), parent=blog_key())
		memcache.set(key, entry)
		memcache.set('time|%s' % entry_id, datetime.now())
	return entry


class BlogPage(Handler):
	def get(self):
		entries = top_entries()
		#select whether to render json or html
		if self.format == 'html':
			last_query = datetime.now() - memcache.get("time")
			self.render('front.html', entries=entries, last_query=last_query)
		else:
			self.render_json([e.as_dict() for e in entries])


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


class Logout(Handler):
	def get(self):
		self.logout()
		self.redirect('/blog/signup')


class Welcome(Handler):
	def get(self):
		if self.user:
			self.render("welcome.html", username=self.user.username)
		else:
			self.redirect('/blog/signup')


class Permalink(Handler):
	def get(self, entry_id):
		entry = get_entry(entry_id)
		if not entry:
			self.error(404)
			return
		if self.format == 'html':
			last_query = datetime.now() - memcache.get('time|%s' % entry_id)
			self.render('permalink.html', entry=entry, last_query=last_query)
		else:
			self.render_json(entry.as_dict())


class NewPost(Handler):
	def render_newpost(self, subject='', content='', error=''):
		self.render('newpost.html', subject=subject, content=content, error=error)

	def get(self):
		self.render_newpost()

	def post(self):
		subject = self.request.get('subject')
		content = self.request.get('content')

		if subject and content:
			e = Post(subject=subject, content=content, parent=blog_key())
			e.put()

			top_entries(True)
			self.redirect('/blog/%s' % e.key().id())
		else:
			error = 'we need both a subject and content!'
			self.render_newpost(error=error, subject=subject, content=content)


class Flush(Handler):
	def get(self):
		memcache.flush_all()
		self.redirect('/blog/signup')


app = webapp2.WSGIApplication([
    ('/blog/?(?:\.json)?', BlogPage),
    ('/blog/signup', Register),
    ('/blog/welcome', Welcome),
    ('/blog/(\d+)/?(?:.json)?', Permalink),
    ('/blog/newpost', NewPost),
    ('/blog/login', Login),
    ('/blog/logout', Logout),
    ('/blog/flush/?', Flush)
    ], debug=True)