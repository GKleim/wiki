"""`main` is the top level module for your Flask application."""

# Import the Flask Framework
from flask import Flask, render_template, redirect, url_for
from entities import *
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
def login():
	if request.method == 'POST':
		username = request.form['username']
		password = request.form['password']

		user = User.login(username, password)

		if user:
			session['username'] = username
			redirect(url_for('welcome', username=username))
		else:
			redirect(url_for('signup'))

	return render_template('login.html')


@app.route('/welcome')
def logout():
	username = session['username']
	return render_template('welcome.html')


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
