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
from google.appengine.ext import ndb
from google.appengine.api import memcache
from datetime import datetime, timedelta
from entities import *
from utils import *
from handler import Handler
from accounts import Welcome, Register, Login, Logout
from webapp2 import uri_for

# WikiPage renders a page in the wiki
# Improvements:
#   Homepage ("/")
#   (1) List the top 10 most recent links
#   (2) Show the title (url), and first few lines of content
#   All
#   (3) This handler matches the regex: [a-z]+. In the future we may
#       want to allow capitals (but convert to all lowercase for a match).
#       Also may want to allow the minus sign '-' to represent a space. When
#       rendering the page title, the works will be split and capitalized based
#       on the location of the minus signs.
class WikiPage(Handler):
	def render_wikipage(self, content='', page_tag=''):
		self.render('wikipage.html', content=content, page_tag=page_tag)

	def get(self, page_tag):
		# a blank url is equivalent to the homepage
		if page_tag == '':
			self.redirect(uri_for('home'))
			return

		# query for Page entity corresponding to the page_tag
		page = Page.by_tag(page_tag)

		# if there is a matching page in the database, return the page
		if page:
			content = get_content(page)
			self.render_wikipage(content=content.content, page_tag=page_tag)
			# self.write("WikiPage | %s" % page_tag)
		# if the there is not a matching page in the database, go to edit page
		else:
			self.redirect(uri_for('edit', page_tag=page_tag))


# EditPage renders an edit interface for a page in the wiki
# If a Page entity does not exist for url, the page entity is displayed
class EditPage(Handler):
	def render_editpage(self, page_tag='', content=''):
		if content == '':
			content = 'The requested page does not exist.\n'
			content += 'To create the page, enter in this text field and click "save".'
		self.render('editpage.html', page_tag=page_tag, content=content)

	def get(self, page_tag):
		# if a user is logged in, allow the page to be edited
		if self.user:
			page = Page.by_tag(page_tag)
			if page:
				content = get_content(page)
				self.render_editpage(page_tag=page_tag, content=content.content)
				# self.write("WikiPage | edit | %s" % page_tag)
			else:
				self.render_editpage(page_tag=page_tag)
		else:
			self.redirect(uri_for('login'))

	def post(self, page_tag):
		user_content = self.request.get('content')

		# query for Page entity correseponding to the page_tag (DRY)
		p = Page.by_tag(page_tag)

		# if there is no matching page, create the page.
		# This code is in the post method so pages only get created if the user
		# has created content for the page.
		if not p:
			p = Page(tag=page_tag, owner=self.user.username,
				     edits = 0, parent=wiki_key())
			p.put()

		# create content entity with parent p
		c = Content(content=user_content, author=self.user.username, parent=p.key)
		c.put()

		p.edits += 1
		p.put()

		# render the page with the new content
		self.redirect(uri_for('wikipage', page_tag=page_tag))


# HistoryPage renders the content history for a page in the wiki
class HistoryPage(Handler):
	def get(self, page_tag):
		self.write("WikiPage | history | %s" % page_tag)


# HomePage renders the homepage of the wiki
class HomePage(Handler):
	def render_homepage(self, newest_pages=[], updated_pages=[]):
		self.render('home.html', newest_pages=newest_pages,
			                     updated_pages=updated_pages)

	def get(self):
		self.render_homepage(newest_pages=newest_pages(),
			                 updated_pages=newest_page_updates())
		# self.write("WikiPage | home")


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

			self.redirect('/blog/%s' % e.key.id())
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

# PAGE_RE is the regex for wikipage url names
# Improvements:
#   (1) ignore matches with strings starting with "_". Currently the list order
#       in the argument for app matters
#   (2) since I added extended routes, "/?" won't work for adding an option slash
PAGE_RE = r'/<page_tag:((?:[a-zA-Z0-9_-]+)*)>'

app = webapp2.WSGIApplication([
    webapp2.Route(r'/signup', handler=Register, name='signup'),
    webapp2.Route(r'/welcome', handler=Welcome, name='welcome'),
    webapp2.Route(r'/(\d+)/?(?:.json)?', handler=Permalink, name='permalink'),
    webapp2.Route(r'/blog/newpost', handler=NewPost, name='newpost'),
    webapp2.Route(r'/login', handler=Login, name='login'),
    webapp2.Route(r'/logout', handler=Logout, name='logout'),
    webapp2.Route(r'/flush', handler=Flush, name='flush'),
    webapp2.Route(r'/edit' + PAGE_RE, handler=EditPage, name='edit'),
    webapp2.Route(r'/history' + PAGE_RE, handler=HistoryPage, name='history'),
    webapp2.Route(r'/home', handler=HomePage, name='home'),
    webapp2.Route('/wiki'+PAGE_RE, handler=WikiPage, name='wikipage')
    ], debug=True)
	# debug = True --> show python tracebacks in the browser