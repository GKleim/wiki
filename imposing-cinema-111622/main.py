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

# main.py
# This .py file contains the url to handler mappings and the core request handlers
# Improvements:
#	(1) If the site gets larger, I may want to start grouping out the core request handlers
#       into other .py files

import webapp2, json
from google.appengine.ext import db
from google.appengine.api import memcache
from datetime import datetime, timedelta
from entities import *
from utils import *
from handler import Handler
from accounts import Welcome, Register, Login, Logout

# WikiPage renders a page in the wiki
# Improvements:
#   (1) List the top 10 most recent links
#   (2) Show the title (url), and first few lines of content
#   (3) This handler matches the regex: [a-z]+. In the future we may
#       want to allow capitals (but convert to all lowercase for a match).
#       Also may want to allow the minus sign '-' to represent a space. When
#       rendering the page title, the works will be split and capitalized based
#       on the location of the minus signs.
class WikiPage(Handler):
	def get(self, title):
		self.write("WikiPage | %s" % title)


# Permalink renders a single blog post
# Improvements:
#   (1) May want to abstract out the memecache gets
class Permalink(Handler):
	def get(self, entry_id):
		# assign the requested entry object to entry
		entry = get_entry(entry_id)

		if not entry:
			self.error(404)
			return
		if self.format == 'html':
			# last_query is the time since the last db_query for the given entry
			last_query = datetime.now() - memcache.get('time|%s' % entry_id)

			self.render('permalink.html', entry=entry, last_query=last_query)
		else:
			self.render_json(entry.as_dict())


# NewPost renders the new post input form and handles post submissions
# Improvements:
#   (1) The site is simple at this point. In the future we may want to add
#       more complicated content validation. At that point we would need more
#       helper functions
class NewPost(Handler):
	def render_newpost(self, subject='', content='', error=''):
		self.render('newpost.html', subject=subject, content=content, error=error)

	def get(self):
		self.render_newpost()

	def post(self):
		subject = self.request.get('subject')
		content = self.request.get('content')

		# if subject and content is present, create a new entry row in the db
		if subject and content:
			e = Post(subject=subject, content=content, parent=blog_key())
			e.put()

			# The True argument tells top_entries to rerun the db query. Performance
			# is improved by having the db query run only when a new post is added to
			# the db.
			top_entries(True)

			self.redirect('/blog/%s' % e.key().id())
		else:
			error = 'we need both a subject and content!'
			self.render_newpost(error=error, subject=subject, content=content)

# The Flush class is shortcut for clearing memcache.
# Improvements:
#   (1) This request handler is taking up space in this file and it is not a core handler.
class Flush(Handler):
	def get(self):
		memcache.flush_all()
		self.redirect('/blog/signup')


# url to request handler mapping
# debug = True --> show python tracebacks in the browser
app = webapp2.WSGIApplication([
    ('/([a-z]+)/?(?:.json)?', WikiPage),
    ('/_signup', Register),
    ('/_welcome', Welcome),
    ('/(\d+)/?(?:.json)?', Permalink),
    ('/blog/newpost', NewPost),
    ('/_login/?', Login),
    ('/_logout/?', Logout),
    ('/_flush/?', Flush)
    ], debug=True)