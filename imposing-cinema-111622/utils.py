# utils.py
# This .py file contains common utility functions.
# This file should not contain app specific functions

import re
import hmac, random, string
import hashlib

# Form validation functions
# Improvements:
#	(1) Set a required format for passwords us regex. i.e. 1 capital, 1 number, etc.
USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return USER_RE.match(username)

EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")
def valid_email(email):
    return EMAIL_RE.match(email)

def valid_password(password,verify):
	return password == verify


# Secure user cookie functions
# Improvements:
#	(1) Use bcrypt library for hashes instead of sha256. bcrypt is the most secure hash.
SECRET = 'secret'

def hash_str(s):
	return hmac.new(SECRET,s).hexdigest()

def make_secure_val(s):
	return '%s|%s' % (s, hash_str(s))

def check_secure_val(h):
	val = h.split('|')[0]
	if h == make_secure_val(val):
		return val


# Secure password handling functions
# Improvements:
#	(1) Use bcrypt library for hashes instead of sha256. bcrypt is the most secure hash.
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