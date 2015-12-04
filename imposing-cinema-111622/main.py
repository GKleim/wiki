"""`main` is the top level module for your Flask application."""

# Import the Flask Framework
from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask.views import View
from entities import *
from utils import *
app = Flask(__name__)
# secret key for sessions. This needs to be a random file and kept safe
app.secret_key = 'secret'
# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.


# home renders the homepage of the wiki
# Improvements:
#   (1) Show the most recently updated/created pages in a different way. Right now
#       the pages are represented by their tags which are ugly (i.e. Houston_Texas).
#       May want to write a parsing function to format the text that is displayed.
#   (2) Add a wikipage search or an alphabetical index?
#   (3) Add an info webpage the describes how to use the wiki
@app.route('/')
@app.route('/wiki')
@app.route('/home')
def home(newe_pages=None, update_pages=None):
    new_pages = newest_pages()
    update_pages = newest_page_updates()
    return render_template('home.html',
                            newest_pages=new_pages,
                            updated_pages=update_pages)


# wikipage renders a page in the wiki
# Improvements:
#   (1) There is alot of identical code in the WikiPage and EditPage handlers
#       Reoragnize the code to prevent the retyping.
@app.route('/wiki/<page_tag>')
def wikipage(page_tag):
    # query for Page entity corresponding to the page_tag
    page = Page.by_tag(page_tag)
    # get version parameter value (/..?v=#)
    # The version number is sent when redirecting from a history page
    version = request.args.get('v')
    # if there is a matching page in the database, return the page
    if page:
        title = underscore_to_space(page_tag)
        if version and int(version) > 0:
            content = get_history(page)[int(version)].content
        else:
            content = get_content(page).content
        return render_template('wikipage.html',
                                content=content,
                                page_tag=page_tag,
                                title=title)
    # if the there is not a matching page in the database, go to edit page
    else:
        flash('The requested page does not exist.')
        return redirect(url_for('edit', page_tag=page_tag))


# edit renders an edit interface for a page in the wiki
# If a Page entity does not exist for url, the page entity is displayed
# Improvements:
#   (1) The edit and history lines should not be shown on the webpage when at the
#       webpage or other utility type pages (signin, info, etc.)
#   (2) I feel like there is a way to reduce all of the query calls, but I have not
#       looked at the code too closely to figure out a better way to do it.
@app.route('/edit/<page_tag>', methods=['GET', 'POST'])
def edit(page_tag, content=None):
    if session.get('username'):
        p = Page.by_tag(page_tag)
        if request.method == 'POST':
            user_content = request.form['content']
            # if there is no matching page, create the page.
            # This code is in the post method so pages only get created if the
            # user has created content for the page.
            if not p:
                p = Page(tag=page_tag, owner=session['username'],
                         edits = 0, parent=wiki_key())
                p.put()
            # create content entity with parent p
            c = Content(content=user_content, author=session['username'],
                        parent=p.key)
            c.put()
            # update the counter for number of saved edits for a page.
            # This is not very elegant, but it was a way for me to force the
            # modified date property in the Page instance to udpate when a new
            # content instance is created.
            p.edits += 1
            p.put()
            # render the page with the new content
            return redirect(url_for('wikipage', page_tag=page_tag))
        # if a user is logged in, allow the page to be edited
        version = request.args.get('v')
        if p:
            if version and int(version) > 0:
                content = get_history(p)[int(version)].content
            else:
                content = get_content(p).content
        if not content:
            content = 'The requested page does not exist.\n'
            content += 'To create the page, enter text in this text area and'
            content += ' click "save".'
        title = underscore_to_space(page_tag)
        return render_template('editpage.html', page_tag=page_tag,
                                content=content,
                                title=title)
    else:
        flash('Log in to create and edit pages')
        return redirect(url_for('login', last=page_tag))


# histroy renders the content history for a page in the wiki
# Improvements:
#   (1) Improve how the history table is displayed. Limit the number of characters
#       shown for the content field?
@app.route('/history/<page_tag>')
def history(page_tag, history=None):
        p = Page.by_tag(page_tag)
        if not p:
            flash('Since the requested page does not exist, no history is available.')
            return redirect(url_for('edit', page_tag=page_tag))
        history = get_history(p)
        title = underscore_to_space(page_tag)
        return render_template('history.html', page_tag=page_tag, history=history,
                                title=title)


@app.route('/login', methods=['GET', 'POST'])
def login(username='', login_error=''):
    if 'username' in session:
        flash('You are already logged in. Log out to sign in as a different user.')
        return redirect(url_for('welcome'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # return user if username/pw combo is in database
        user = User.login(username, password)
        if user:
            # set session user
            session['username'] = username
            page_tag = request.args.get('last')
            if page_tag:
                return redirect(url_for('edit', page_tag=page_tag))
            return redirect(url_for('welcome'))
        else:
            login_error = 'invalid login' 
    # GET request is to render the login page 
    return render_template('login.html',
        username=username, login_error=login_error)


# SignUp is the base class for flask signup type view functions
class SignUp(View):
    # specifying the methods as attributes is required?
    methods = ['GET', 'POST']

    # get_template_name is overwritten by child class to pass html page to be
    # rendered
    def get_template_name(self):
        raise NotImplementedError()

    # get_redirect_name is overwritten by child
    # this is the view function to redirect to when a user is already logged in
    def get_redirect_name(self):
        raise NotImplementedError()

    def render_template(self, username='', email='', username_error='',
                        password_error='', verify_error='', email_error=''):
        return render_template(self.get_template_name(), username=username,
                        email=email, username_error=username_error,
                        password_error=password_error,
                        verify_error=verify_error, email_error=email_error)

    def dispatch_request(self):
        if 'username' in session:
            flash('You are already logged in. Log out to register a new user.')
            return redirect(url_for(self.get_redirect_name()))
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


# Register builds on the SignUp base class
class Register(SignUp):
    def get_template_name(self):
        return 'signup.html'

    def get_redirect_name(self):
        return 'welcome'

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
    # redirect to the page the user was viewing
    return redirect(request.referrer)


@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, Nothing at this URL.', 404


@app.errorhandler(500)
def application_error(e):
    """Return a custom 500 error."""
    return 'Sorry, unexpected error: {}'.format(e), 500
