######################################
# author ben lawson <balawson@bu.edu>
# Edited by: Yifan Wang <wyf7107@bu.edu>
######################################
# Some code adapted from
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################

import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
import flask.ext.login as flask_login

#for image uploading
from werkzeug import secure_filename
import os, base64

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

#These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = '87863418Wyf'
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

#begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from Users")
users = cursor.fetchall()

def getUserList():
	cursor = conn.cursor()
	cursor.execute("SELECT email from Users")
	return cursor.fetchall()

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def user_loader(email):
	users = getUserList()
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	return user

@login_manager.request_loader
def request_loader(request):
	users = getUserList()
	email = request.form.get('email')
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	cursor = mysql.connect().cursor()
	cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
	data = cursor.fetchall()
	pwd = str(data[0][0] )
	user.is_authenticated = request.form['password'] == pwd
	return user

'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		return '''
			   <form action='login' method='POST'>
				<input type='text' name='email' id='email' placeholder='email'></input>
				<input type='password' name='password' id='password' placeholder='password'></input>
				<input type='submit' name='submit'></input>
			   </form></br>
		   <a href='/'>Home</a>
			   '''
	#The request method is POST (page is recieving data)
	email = flask.request.form['email']
	cursor = conn.cursor()
	#check if email is registered
	if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
		data = cursor.fetchall()
		pwd = str(data[0][0] )
		if flask.request.form['password'] == pwd:
			user = User()
			user.id = email
			flask_login.login_user(user) #okay login in user
			return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

	#information did not match
	return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"

@app.route('/logout')
def logout():
	flask_login.logout_user()
	return render_template('hello.html', message='Logged out')

@login_manager.unauthorized_handler
def unauthorized_handler():
	return render_template('unauth.html')

#you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
	return render_template('register.html', supress='True')

@app.route("/register", methods=['POST'])
def register_user():
	try:
		email=request.form.get('email')
		password=request.form.get('password')
                firstname=request.form.get('firstname')
                lastname=request.form.get('lastname')
                dob=request.form.get('dob')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	hometown = request.form.get('hometown')
	gender = request.form.get('gender')
	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		print(cursor.execute("INSERT INTO Users (email, password, firstname, lastname, dob, hometown, gender) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')".format(email, password, firstname, lastname, dob, hometown, gender)))
		conn.commit()
		#log user in
		user = User()
		user.id = email
		flask_login.login_user(user)
		return render_template('hello.html', name=email, message='Account Created!')
	else:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('register'))

def getUsersPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]

def getTagPhotos(word):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures,Tags WHERE Tags.word = '{0}' AND Pictures.picture_id = Tags.pic_id".format(word))
	return cursor.fetchall()

def getUserTagPhotos(word):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures,Tags WHERE user_id = {0} AND pic_id = picture_id AND word = '{1}'".format(getUserIdFromEmail(flask_login.current_user.id),word))
	return cursor.fetchall()


def getUserIdFromEmail(email):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
	return cursor.fetchone()[0]

def isEmailUnique(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
		#this means there are greater than zero entries with that email
		return False
	else:
		return True

def isPhotoUsers(photo_id):
	cursor = conn.cursor()
	if cursor.execute("SELECT * FROM Pictures WHERE user_id = {0} AND picture_id = {1}".format(getUserIdFromEmail(flask_login.current_user.id),photo_id)):
		return True
	else:
		return False
#end login code

@app.route('/profile')
@flask_login.login_required
def protected():
	return render_template('hello.html', name=flask_login.current_user.id, message="Here's your profile")

# strat search page

@app.route('/search')
@flask_login.login_required
def search():
	return render_template('search.html')

@app.route('/results/', methods = ['POST', 'GET'])
def results():
	query = '' #Empty string for query
	data = [] #Empty list for data
	if request.method == 'POST': #If a post request is detected
		result = request.form #Get form from request
		print result

		for key in result: #iterate through the dictionary
			if key == 'Query':
				query = "SELECT firstname,lastname,email  FROM Users WHERE email = '{0}'".format(result[key])
		cursor = conn.cursor()
		#try query
		try:
			cursor.execute(query)
			return render_template('index.html', query = query, data = extractData(cursor))
		except:
			print "There is an error in the SQL syntax for: ", query
			return render_template('index.html', query = query, error = 1)
	else: #If a get request is detected
		return render_template('index.html')

def extractData(cursor):
	data = []
	for item in cursor:
		data.append(item)
	return data

#end search page

#start code for adding friend
@app.route('/addfriend')
@flask_login.login_required
def showaddfriend():
	return render_template('addfriend.html')


@app.route('/resultsaddfriend', methods=['GET', 'POST'])
@flask_login.login_required
def addfriend():
	query = '' #Empty string for query
	data = [] #Empty list for data
	if request.method == 'POST': #If a post request is detected
		result = request.form #Get form from request
		print result
		for key in result: #iterate through the dictionary
			if key == 'Query':
				cursor = conn.cursor()
				cursor.execute("INSERT INTO Friends (useremail,friendemail) VALUES ('{0}', '{1}')".format(flask_login.current_user.id,result[key]))
				conn.commit()
			return render_template('okfriend.html')
	else: #If a get request is detected
		return render_template('addfriend.html')

#end code of addfriend
##################################
#start list my friend
@app.route('/listmyfriend')
@flask_login.login_required
def listmyfriendresults():
	query = '' #Empty string for query
	data = [] #Empty list for data
	query = "SELECT friendemail  FROM Friends WHERE useremail = '{0}'".format(flask_login.current_user.id)
	cursor = conn.cursor()
	try:
		cursor.execute(query)
		return render_template('listmyfriend.html', query = query, data = extractData(cursor))
	except:
		print "There is an error in the SQL syntax for: ", query
		return render_template('listmyfriend.html', query = query, error = 1)



#begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS



def isAlbumExists(albumname):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT name  FROM Albums WHERE owner = '{0}' AND name = '{1}'".format((flask_login.current_user.id),albumname)):
		#this means there are greater than zero entries with that email
		return True
	else:
		return False


def getMaxId():
	cursor = conn.cursor()
	cursor.execute("SELECT MAX(picture_id)  FROM Pictures")
	return cursor.fetchone()[0]


@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		imgfile = request.files['photo']
		caption = request.form.get('caption')
		albumname = request.form.get('albumname')
		tagname = request.form.get('tagname')
		tagarr = tagname.split()
		print(caption)
		photo_data = base64.standard_b64encode(imgfile.read())
		test = isAlbumExists(albumname)
		if test:
			cursor = conn.cursor()
			cursor.execute("INSERT INTO Pictures (imgdata, user_id, caption,album_name) VALUES ('{0}', '{1}', '{2}','{3}' )".format(photo_data,uid, caption,albumname))
			conn.commit()
			pic_id = getMaxId()
			for i in range(0,len(tagarr)):
				cursor.execute("INSERT INTO Tags (word,pic_id) VALUES ('{0}', '{1}')".format(tagarr[i],pic_id))
				conn.commit()
			return render_template('hello.html', name=flask_login.current_user.id, message='Photo uploaded!', photos=getUsersPhotos(uid) )
		else:
			return render_template('uploadfail.html')
	#The method is GET so we return a  HTML form to upload the a photo.
	else:
		return render_template('upload.html')
#end photo uploading code
##################################
@app.route('/browse')
def browseresults():
	query = '' #Empty string for query
	data = [] #Empty list for data
	query = "SELECT imgdata, picture_id, caption FROM Pictures"
	cursor = conn.cursor()
	try:
		cursor.execute(query)
		return render_template('browse.html', photos = extractData(cursor))
	except:
		print "There is an error in the SQL syntax for: ", query
		return render_template('browse.html')
##################################
#start code for showing albums
@app.route('/showalbum')
@flask_login.login_required
def albumresults():
	query = '' #Empty string for query
	data = [] #Empty list for data
	query = "SELECT name FROM Albums WHERE owner = '{0}'".format(flask_login.current_user.id)
	cursor = conn.cursor()
	try:
		cursor.execute(query)
		return render_template('showalbums.html', data = extractData(cursor))
	except:
		print "There is an error in the SQL syntax for: ", query
		return render_template('showalbums.html')
##################################
@app.route("/createalbum", methods=['GET'])
def createalbum():
	return render_template('createalbum.html')

@app.route("/createalbum", methods=['POST'])
def register_album():
	try:
		albumname=request.form.get('albumname')
		doc=request.form.get('dateofcreation')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('createalbum'))
	cursor = conn.cursor()
	cursor.execute("INSERT INTO Albums (name,owner,datecreate) VALUES ('{0}', '{1}', '{2}')".format(albumname, flask_login.current_user.id, doc))
	conn.commit()
		#log user in
	return render_template('okaycreatealbum.html')
##################################
#start code for delete photo
@app.route('/deletephoto')
@flask_login.login_required
def showdeletephoto():
	return render_template('deletephoto.html')


@app.route('/resultsdeletephoto', methods=['GET', 'POST'])
@flask_login.login_required
def deletephoto():
	query = '' #Empty string for query
	data = [] #Empty list for data
	if request.method == 'POST': #If a post request is detected
		result = request.form #Get form from request
		print result
		for key in result: #iterate through the dictionary
			if key == 'Query':
				cursor = conn.cursor()
				cursor.execute("DELETE FROM Tags  WHERE pic_id = '{0}'".format(result[key]))
				conn.commit()
				cursor.execute("DELETE FROM Comments  WHERE pic_id = '{0}'".format(result[key]))
				conn.commit()
				cursor.execute("DELETE FROM Likes  WHERE photo_id = '{0}'".format(result[key]))
				conn.commit()
				cursor.execute("DELETE FROM Pictures  WHERE picture_id = '{0}'".format(result[key]))
				conn.commit()
			return render_template('okdeletephoto.html')
	else: #If a get request is detected
		return render_template('deletephoto.html')

##################################
#start code for delete album
@app.route('/deletealbum')
@flask_login.login_required
def showdeletealbum():
	return render_template('deletealbum.html')


@app.route('/resultsdeletealbum', methods=['GET', 'POST'])
@flask_login.login_required
def deletealbum():
	query = '' #Empty string for query
	data = [] #Empty list for data
	if request.method == 'POST': #If a post request is detected
		result = request.form #Get form from request
		print result
		for key in result: #iterate through the dictionary
			if key == 'Query':
				albumname = result[key]
				test = isAlbumExists(albumname)
				if test:
					cursor = conn.cursor()
					cursor.execute("DELETE FROM Pictures  WHERE album_name = '{0}'".format(result[key]))
					conn.commit()
					cursor.execute("DELETE FROM Albums  WHERE name = '{0}'".format(result[key]))
					conn.commit()
					return render_template('okaydeletealbum.html')
				else:
					return render_template('deletealbumfail.html')
	else: #If a get request is detected
		return render_template('deletealbum.html')

##################################
#start tag photo code
@app.route("/tagphoto", methods=['GET'])
@flask_login.login_required
def tagphoto():
	return render_template('tagphoto.html')

@app.route("/tagphoto", methods=['POST'])
@flask_login.login_required
def register_tag():
	try:
		photo_id=request.form.get('photo_id')
		word=request.form.get('tagword')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('tagphoto'))
	cursor = conn.cursor()
	cursor.execute("INSERT INTO Tags (word,pic_id) VALUES ('{0}', '{1}')".format(word, photo_id))
	conn.commit()
		#log user in
	return render_template('okaycreatealbum.html')

##################################
@app.route('/generalFriend')
@flask_login.login_required
def showgeneralfriend():
	return render_template('generalFriend.html')

##################################
@app.route('/generalTag')
@flask_login.login_required
def showgeneraltag():
	return render_template('generalTag.html')
##################################
#start code for mytagphoto
@app.route('/mytagphoto')
@flask_login.login_required
def listmytagresults():
	query = '' #Empty string for query
	data = [] #Empty list for data
	query = "SELECT DISTINCT t.word FROM Pictures p,Tags t WHERE p.user_id = {0} AND t.pic_id = p.picture_id ".format(getUserIdFromEmail(flask_login.current_user.id))
	cursor = conn.cursor()
	try:
		cursor.execute(query)
		return render_template('mytagphoto.html',  query = query, data = extractData(cursor))
	except:
		print "There is an error in the SQL syntax for: ", query
		return render_template('generalTag.html')
##################################
#start code for all tag photos
@app.route('/alltagphoto')
@flask_login.login_required
def listalltagresults():
	query = '' #Empty string for query
	data = [] #Empty list for data
	query = "SELECT DISTINCT word FROM Tags "
	cursor = conn.cursor()
	try:
		cursor.execute(query)
		return render_template('alltagphoto.html',  query = query, data = extractData(cursor))
	except:
		print "There is an error in the SQL syntax for: ", query
		return render_template('generalTag.html')
##################################
#start code for all tag details
@app.route('/alltagdetail/<word>', methods = ['GET'])
@flask_login.login_required
def alltagdetail(word):
		return render_template('alltagdetail.html', photos = getTagPhotos(word))
##################################
@app.route('/usertagdetail/<word>', methods = ['GET'])
@flask_login.login_required
def usertagdetail(word):
		return render_template('alltagdetail.html', photos = getUserTagPhotos(word))

##################################
#start code for poplar tags
@app.route('/populartag')
@flask_login.login_required
def listpopulartagresults():
	query = '' #Empty string for query
	data = [] #Empty list for data
	query = "SELECT T.word from (SELECT word, COUNT(*) AS magnitude  FROM Tags GROUP BY word ORDER BY magnitude DESC LIMIT 5) as T "
	cursor = conn.cursor()
	cursor.execute(query)
	return render_template('populartag.html',  query = query, data = extractData(cursor))

##################################
#start code for photo search
@app.route('/photosearch')
def photosearch():
	return render_template('photosearch.html')

@app.route('/photosearchresults/', methods = ['POST', 'GET'])
def photosearchresults():
	query = '' #Empty string for query
	data = [] #Empty list for data
	if request.method == 'POST': #If a post request is detected
		result = request.form #Get form from request
		print result
		for key in result: #iterate through the dictionary
			if key == 'Query':
				tagarr = result[key].split()
				print(tagarr)
				if len(tagarr) == 1:
					query = "SELECT imgdata, picture_id, caption  FROM Pictures,Tags WHERE word = '{0}' and pic_id = picture_id".format(tagarr[0])
				if len(tagarr) == 2:
					query = "SELECT imgdata, picture_id,caption FROM Pictures P,(select t1.pic_id from Tags t1, Tags t2 where t1.word='{0}' and t2.word='{1}' and t1.pic_id = t2.pic_id) as T where T.pic_id = P.picture_id".format(tagarr[0],tagarr[1])
				if len(tagarr) == 3:
					query = "SELECT imgdata, picture_id,caption FROM Pictures P,(select t1.pic_id from Tags t1, Tags t2, Tags t3 where t1.word='{0}' and t2.word='{1}' and t3.word='{2}' and t1.pic_id = t2.pic_id and t1.pic_id = t3.pic_id) as T where T.pic_id = P.picture_id".format(tagarr[0],tagarr[1],tagarr[2])
				if len(tagarr) == 4:
					query = "SELECT imgdata, picture_id,caption FROM Pictures P,(select t1.pic_id from Tags t1, Tags t2, Tags t3, Tags t4 where t1.word='{0}' and t2.word='{1}' and t3.word='{2}' and t4.word = '{3}' and t1.pic_id = t2.pic_id and t1.pic_id = t3.pic_id and t1.pic_id = t4.pic_id) as T WHERE T.pic_id = P.picture_id".format(tagarr[0],tagarr[1],tagarr[2],tagarr[3])
		cursor = conn.cursor()
		cursor.execute(query)
		return render_template('browse.html', photos = extractData(cursor))
	else: #If a get request is detected
		return render_template('photosearch.html')

##################################
#start code for Comments
@app.route("/comment", methods=['GET'])
def showcomment():
	return render_template('comment.html', supress='True')

@app.route("/comment", methods=['POST'])
def register_comment():

	picture_id=request.form.get('picture_id')
	content=request.form.get('content')
    	doc=request.form.get('doc')
	cursor = conn.cursor()
	if flask_login.current_user.id != "" and flask_login.current_user.id != 'NULL':
		if not isPhotoUsers(picture_id):
			cursor.execute("INSERT INTO Comments (content, owner, doc, pic_id) VALUES ('{0}', '{1}', '{2}', {3})".format(content,flask_login.current_user.id,doc,picture_id))
			conn.commit()
			return render_template('okcomment.html')
		else:
			return render_template('failcomment.html')
	else:
		cursor.execute("INSERT INTO Comments (content, owner, doc, pic_id) VALUES ('{0}', '{1}', '{2}', {3})".format(content,'guest@guest.com',doc,picture_id))
		conn.commit()
		return render_template('okcomment.html')

##################################
#start code for like photos

def getnumlike(photoid):
	cursor = conn.cursor()
	cursor.execute("SELECT COUNT(*) FROM Likes WHERE photo_id = {0}".format(photoid))
	return cursor.fetchone()[0] #NOTE list of tuples, [(imgdata, pid), ...]

def getlikelist(photoid):
	cursor = conn.cursor()
	cursor.execute("SELECT useremail FROM Likes WHERE photo_id = {0}".format(photoid))
	return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]


@app.route('/likephoto/<photoid>', methods = ['GET','POST'])
@flask_login.login_required
def likephotos(photoid):
	cursor = conn.cursor()
	cursor.execute("INSERT INTO Likes (useremail,photo_id) VALUES ('{0}',{1})".format(flask_login.current_user.id,photoid))
	conn.commit()
	return render_template('okaylike.html', photoid = photoid, numlike = getnumlike(photoid), likelist = getlikelist(photoid))

@app.route('/seelikelist/<photoid>', methods = ['GET','POST'])
@flask_login.login_required
def seelikephotos(photoid):
	return render_template('okaylike.html', photoid = photoid, numlike = getnumlike(photoid), likelist = getlikelist(photoid))
##################################
#start code for recommand photos
@app.route('/recommandation')
@flask_login.login_required
def listallrecommandations():
	query = '' #Empty string for query
	data = [] #Empty list for data
	occ = []
	query = "SELECT T.word FROM (SELECT word, COUNT(*) AS magnitude  FROM Tags,Pictures WHERE user_id = {0} and pic_id = picture_id GROUP BY word ORDER BY magnitude DESC LIMIT 5) as T".format(getUserIdFromEmail(flask_login.current_user.id))
	cursor = conn.cursor()
	cursor.execute(query)
	tagarr = cursor.fetchall()
 	query = "SELECT picture_id FROM Pictures P,(select t1.pic_id from Tags t1, Tags t2, Tags t3, Tags t4, Tags t5 where t1.word='{0}' and t2.word='{1}' and t3.word='{2}' and t4.word = '{3}' and t5.word = '{4}' and t1.pic_id = t2.pic_id and t1.pic_id = t3.pic_id and t1.pic_id = t4.pic_id and t1.pic_id = t5.pic_id) as T WHERE T.pic_id = P.picture_id".format(tagarr[0][0],tagarr[1][0],tagarr[2][0],tagarr[3][0],tagarr[4][0])
	cursor.execute(query)
	res = cursor.fetchall()
	for i in range(0,len(res)):
		occ.append(res[i][0])
	query = "SELECT picture_id FROM Pictures P,(select t1.pic_id from Tags t1, Tags t2, Tags t3, Tags t4 where t1.word='{0}' and t2.word='{1}' and t3.word='{2}' and t4.word = '{3}' and t1.pic_id = t2.pic_id and t1.pic_id = t3.pic_id and t1.pic_id = t4.pic_id) as T WHERE T.pic_id = P.picture_id".format(tagarr[0][0],tagarr[1][0],tagarr[2][0],tagarr[3][0])
	cursor.execute(query)
	res = cursor.fetchall()
	for i in range(0,len(res)):
		occ.append(res[i][0])
	query = "SELECT picture_id FROM Pictures P,(select t1.pic_id from Tags t1, Tags t2, Tags t3 where t1.word='{0}' and t2.word='{1}' and t3.word='{2}' and t1.pic_id = t2.pic_id and t1.pic_id = t3.pic_id) as T where T.pic_id = P.picture_id".format(tagarr[0][0],tagarr[1][0],tagarr[2][0])
	cursor.execute(query)
	res = cursor.fetchall()
	for i in range(0,len(res)):
		occ.append(res[i][0])
	query = "SELECT picture_id FROM Pictures P,(select t1.pic_id from Tags t1, Tags t2 where t1.word='{0}' and t2.word='{1}' and t1.pic_id = t2.pic_id) as T where T.pic_id = P.picture_id".format(tagarr[0][0],tagarr[1][0])
	cursor.execute(query)
	res = cursor.fetchall()
	for i in range(0,len(res)):
		occ.append(res[i][0])
	query = "SELECT picture_id  FROM Pictures,Tags WHERE word = '{0}' and pic_id = picture_id".format(tagarr[0][0])
	cursor.execute(query)
	res = cursor.fetchall()
	for i in range(0,len(res)):
		occ.append(res[i][0])
	s_acc = sorted(occ,key=occ.count,reverse=True)
	seen = set()
	res_id =[x for x in s_acc if not (x in seen or seen.add(x))]
	print(res_id)

	q = "SELECT imgdata, picture_id, caption from Pictures where picture_id = {0}".format(res_id[0])
	for i in range(1,len(res_id)): q += " or picture_id = {0}".format(res_id[i])
	cursor.execute(q)
	return render_template('recommandation.html',   photos = extractData(cursor))
##################################
#start code for user activity
@app.route('/greatuser',methods = ['GET','POST'])
def showgreatuser():
	cursor = conn.cursor()
	query = "SELECT email from Users,(SELECT T.user_id from (SELECT user_id,COUNT(*) AS magnitude  FROM Pictures GROUP BY user_id ORDER BY magnitude DESC LIMIT 10) as T) as TS where TS.user_id = Users.user_id"
	cursor.execute(query)
	return render_template('greatuser.html',query = query, data1 = extractData(cursor))

##################################
#default page
@app.route("/", methods=['GET'])
def hello():
	return render_template('hello.html', message='Welecome to Photoshare')


if __name__ == "__main__":
	#this is invoked when in the shell  you run
	#$ python app.py
	app.run(port=5000, debug=True)
