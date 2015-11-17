from google.appengine.ext import db
from google.appengine.api import memcache
from datetime import datetime, timedelta
from utils import make_pw_hash, valid_pw

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