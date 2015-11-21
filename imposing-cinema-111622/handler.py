# handler.py
# This .py file contains a base handler class with helpful methods
# This file should only contain the Handler base class and associated functions

import webapp2, jinja2, json
import os
from utils import make_secure_val, check_secure_val
from entities import User

# jinja2 templating: setup code
# template_dir is the path to the template dir. The code assumes the templates
# dir is located in the same directory as the handler.py file (__file__ is the
# current file)
template_dir = os.path.join(os.path.dirname(__file__), 'templates')

# Create an instance of the jinja2 environment.
# autoescape = True --> html is automatically escaped. Text recognized as safe
# can be opted out of autoescape using the word "safe" in the template
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
									autoescape = True)

# Set global values so the webapp2 uri_for() function can be used in templates
jinja_env.globals = {
    'uri_for': webapp2.uri_for
}


# The Handler class is the base class for all request handlers. It adds a layer
# of abstraction to certain routine actions
class Handler(webapp2.RequestHandler):
    # The write function simply makes writing out to the browser less verbose
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    # render_string returns an html string generated using jinja2 templating
    def render_str(self, template, **params):
    	t = jinja_env.get_template(template)
    	return t.render(params)

    # render writes out to the browser using a template and dictionary of params
    def render(self, template, **kw):
        # the login_name variable is used to pass the current user name to all templates
        # via the base.html template. The base.html template is necer called bt itself
        # since it is a wrapper template.
    	login_name = None
    	if self.user:
    		user = self.user
    		login_name = user.username

    	self.write(self.render_str(template, login_name=login_name, **kw))

    # render_json converts a python string to JSON and renders it in the browser
    def render_json(self, d):
        # the dumps(str) method converts a python string to JSON
    	json_text = json.dumps(d)

        # set the Content-Type to JSON (as opposed to text/html)
    	self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'

    	self.write(json_text)

    # The set_secure_cookie sets the cookie "name" to the value "val" in the response header
    def set_secure_cookie(self, name, val):
        # secure the value "val" (probably through hashing)
    	cookie_val = make_secure_val(val)

        # generate the response header
    	self.response.headers.add_header(
    		'Set-Cookie',
    		'%s=%s; Path=/' % (name, cookie_val)) # can include Expires param

    # The read_secure_cookie function returns the cookie_val if it is secure
    def read_secure_cookie(self, name):
        # cookie_val is assigned the value of the cookie named "name"
    	cookie_val = self.request.cookies.get(name)

        # return the cookie value if the secure value is valid
        # (note: special python syntax used in place of an if statement)
    	return cookie_val and check_secure_val(cookie_val)

    # log "user" in my setting the user_id cookie in the browser
    def login(self, user):
    	self.set_secure_cookie('user_id', str(user.key.id()))   	

    # log out the current user by setting the user_id cookie to nothing
    def logout(self):
    	self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    # The initialize function runs every time the Handler or childer classes are called
    # i.e. on a page request (?)
    def initialize(self, *a, **kw):
        # I am not sure why the webapp2 initialize method is called below
    	webapp2.RequestHandler.initialize(self, *a, **kw)

        # assign the user_id stored in the cookie to uid variable
    	uid = self.read_secure_cookie('user_id')

        # assign user object to the user instance variable
    	self.user = uid and User.by_id(int(uid))

        # assign the output formatting to the format instance variable
    	if self.request.url.endswith('.json'):
    		self.format = 'json'
    	else:
    		self.format = 'html'