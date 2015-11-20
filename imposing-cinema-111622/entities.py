# entities.py
# This .py file contains datastore entities and related functions
# This file should only contain datastore entitiy classes and related memcache queries.
# Improvement:
#	(1) May want to organize memchache a bit better.

from google.appengine.ext import db
from google.appengine.api import memcache
from datetime import datetime, timedelta
from utils import make_pw_hash, valid_pw


# Page entity
# The Page entity represents rows of versions of wiki page content

# The wiki_key function returns the parent key for wikis.
# Having a parent key guarantees consistency when querying immediately after creation (?)
def wiki_key(name = 'default'):
	return db.Key.from_path('wikis', name)

class Page(db.Model):
	tag = db.StringProperty(required = True)
		# doubles as the URL?
	owner = db.StringProperty(required = True)
		# default owner is the user who wrote the first entry
	created = db.DateTimeProperty(auto_now = True)


# Content entity
# The Content entity represents rows of versions of wiki page content

# A Page entity will be the parent of 1 or more Content entities. Only the most recently
# created content entity is displayed for the page. A collection of content entities are
# a history of the changes made to the content displayed at the Page entity URL.

# Having a parent key guarantees consistency when querying immediately after creation (?)
# Improvements:
#   (1) JSON?
#   (2) Review process for Content changes. Changes are sent to Page.owner for review.
# Organization:
#   -- wikipages are organized with the following structure:
#      /wikis
#         /example-page-1 (Page entity)
#            Content entity: example-page-1 revision 0 content
#            Content entity: example-page-1 revision 1 content
#            etc.
#         /example-page-2 (Page entity)
#            Content entity: example-page-2 revision 0 content
#            Content entity: example-page-2 revision 1 content
#            etc.
#         /etc.
#   -- the content of wikipage "A" is stored as a collection of Content entities at path
#      /wikis/Page entity/
#   -- the most recent Content entity is displayed for a given url (store only 10 most recent?)
class Content(db.Model):
	content = db.TextProperty(required = True)
		# Text property stores up to 1 MB and cannot be indexed
	author = db.StringProperty(required = True)
		# stores User.username (you must be a registered user to generate content) 
	created = db.DateTimeProperty(auto_now = True)


# User entity
# The User entity represents rows of user accounts

# The users_key function returns the parent key for users.
# Having a parent key guarantees consistency when querying immediately after creation (?)
def users_key(group = 'default'):
	return db.Key.from_path('users', group)

class User(db.Model):
	username = db.StringProperty(required = True)
	password = db.StringProperty(required = True)
	email = db.StringProperty()
	joined = db.DateTimeProperty(auto_now_add = True)

	# NOTE: @classmethods are methods called on classes, not instances of classes

	# The by_id classmethod returns the user object corresponding to the user id (uid)
	@classmethod
	def by_id(cls, uid):
		return cls.get_by_id(uid, parent = users_key())

	# The by_name classmethod returns the user object corresponding to the username
	@classmethod
	def by_name(cls, username):
		u = cls.all().filter('username =', username).get()
		return u

	# The register classmethod creates a new User object and handles password hashing
	@classmethod
	def register(cls, username, password, email = None):
		password = make_pw_hash(username, password)
		return cls(parent = users_key(),
					username = username,
					password = password,
					email = email)

	# The login classmethod signs the user into the website
	@classmethod
	def login(cls, username, password):
		u = cls.by_name(username)
		if u and valid_pw(username, password, u.password):
			return u


# Post entity
# The Post entity represents rows of blog posts (sometimes called entries)

# The blog_key function returns the parent key for posts.
# Having a parent key guarantees consistency when querying immediately after creation (?)
def blog_key(name = 'default'):
	return db.Key.from_path('blogs', name)

class Post(db.Model):
	subject = db.StringProperty(required = True)
	content = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)
	modified = db.DateTimeProperty(auto_now = True)

	# The as_dict function converts the Post object into a dictionary to be jsonified
	def as_dict(self):
		time_fmt = '%c'
		d = {"subject": self.subject,
	         "content": self.content,
	         "created": self.created.strftime(time_fmt),
	         "modified": self.modified.strftime(time_fmt)}
		return d

# The top_entries function returns the entries to be displayed on the homepage
# This function uses memcache to ensure the query is run only when a new entry is added to the
# datastore.
# Improvements:
#	(1) Add newly added entry to memcache without calling a query (imporves performance)
def top_entries(update = False):
	key = 'top'
	entries = memcache.get(key)
	if entries is None or update:
		# print 'DB Query' when the query is run (for debugging)
		print 'DB Query'

		#database query for posts
		entries = Post.all().ancestor(blog_key()).order("-created").run(limit=10)

		#db is not queried until something is ran on entries. Make a list out of the
		#query to force the query to run. This prevents potentially running the query
		#multiple times in later code
		entries = list(entries)

		memcache.set(key, entries)

		# "time" is stored for displaying the latest query on the webpage
		memcache.set("time", datetime.now())
	return entries

# The get_entry function returns the requested entry
# This function stores the entries in memcache when they are created
def get_entry(entry_id):
	key = '%s' % entry_id
	entry = memcache.get(key)
	if entry is None:
		#database query for post with entry_id
		entry = Post.get_by_id(int(entry_id), parent=blog_key())
		memcache.set(key, entry)

		# A "time" key is created for each entry for display on webpage
		memcache.set('time|%s' % entry_id, datetime.now())
	return entry