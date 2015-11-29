"""`main` is the top level module for your Flask application."""

# Import the Flask Framework
from flask import Flask, render_template, redirect, url_for, request, session
from flask.views import View
from entities import *
from utils import *
app = Flask(__name__)
app.secret_key = 'secret'
# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.


@app.route('/')
@app.route('/home')
@app.route('/wiki')
def home():
    newest_pages=[]
    updated_pages=[]
    return render_template('home.html',
                            newest_pages=newest_pages,
                            updated_pages=updated_pages)


PAGE_RE = r'/<page_tag:((?:[a-zA-Z0-9_-]+)*)>'

@app.route('/wiki/<page_tag>/')
def wikipage(page_tag):
    page = Page.by_tag(page_tag)
    if page:
        content = get_content(page)
        return render_template('wikipage.html',
                                content=content.content,
                                page_tag=page_tag)
    else:
        return redirect(url_for('edit', page_tag=page_tag))


@app.route('/edit/<page_tag>')
def edit(page_tag):
    return 'hello'


@app.route('/login', methods=['GET', 'POST'])
def login(username='', login_error=''):
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print username
        print password
        user = User.login(username, password)
        user2 = User.by_name(username)
        u_ancestor = User

        if user:
            session['username'] = username
            return redirect(url_for('welcome'))
        else:
            login_error = 'invalid login'
            
    return render_template('login.html',
        username=username, login_error=login_error)


class SignUp(View):
    methods = ['GET', 'POST']

    # get_template_name is overwritten by child class to pass html page to be
    # rendered
    def get_template_name(self):
        raise NotImplementedError()

    def render_template(self, username='', email='', username_error='',
                        password_error='', verify_error='', email_error=''):
        return render_template(self.get_template_name(), username=username,
                        email=email, username_error=username_error,
                        password_error=password_error,
                        verify_error=verify_error, email_error=email_error)

    def dispatch_request(self):
        if request.method == 'POST':
            # have_error is True if any of the inputs do not pass validation
            have_error = False
            # assign form data to instance variables
            self.username = request.form['username']
            self.password = request.form['password']
            self.verify = request.form['verify']
            self.email = request.form['email']
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
            # checks for compliant password (password and verify fields)
            elif not valid_password(self.password,self.verify):
                have_error = True
                params['verify_error'] = 'passwords did not match'
            # checks for valid email if an email was entered
            if self.email and not valid_email(self.email):
                have_error = True
                params['email_error'] = 'please enter a valid email'
            # if input does not pass validation, render html with error messages
            if have_error:
                return self.render_template(**params)
            else:
                return self.done(**params)
        # if input passes validation, take the action of the done function
        else:
            return self.render_template()
    
    # The done function is meant to be written over by child class to modify
    # the action taken after a POST request
    def done(self, *a, **kw):
        raise NotImplementedError


class Register(SignUp):
    def get_template_name(self):
        return 'signup.html'

    def done(self, *a, **kw):
        # query User entities for the submitted username
        u = User.by_name(self.username)
        # throw an error message if the username is already taken
        if u:
            msg = 'user is already registered'
            return self.render_template(username_error=msg, **kw)
        # register user if username is not taken
        else:
            # call register classmethod on User to create a new User in the db
            u = User.register(self.username, self.password, self.email)
            u.put()
            # automatically log the user in and redirect to the welcome page
            # redirect requires code 307 to redirect as POST
            return redirect(url_for('login'), code=307)

app.add_url_rule('/signup', view_func=Register.as_view('signup'))


@app.route('/welcome')
def welcome(username=''):
    if 'username' in session:
        username = session['username']
    return render_template('welcome.html', username=username)


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))


@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, Nothing at this URL.', 404


@app.errorhandler(500)
def application_error(e):
    """Return a custom 500 error."""
    return 'Sorry, unexpected error: {}'.format(e), 500
