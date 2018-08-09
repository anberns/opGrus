import os
import time
import uuid
import json
import sys
import crawler
import requests
from socket import error as SocketError
import errno
from flask import Flask, flash, request, render_template, make_response, session, redirect, url_for
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from flask_sockets import Sockets

application = Flask(__name__)
application.secret_key = os.urandom(24)

application.config["MONGO_URI"] = "mongodb+srv://anberns:Yogi1001!@cluster0-bx1le.mongodb.net/test?retryWrites=true"
mongo = PyMongo(application)
sockets = Sockets(application)

# index page with form
@application.route('/')
def index():
	global userId
	userId = request.cookies.get('userId')

	if userId:
		# get stored data
		test = mongo.db.test  # access test collection
		storedCrawls = test.find({'userId': userId})
		return render_template('index.html', crawls=storedCrawls)
	else:
		userId = str(uuid.uuid4())
		response = make_response(render_template('index.html'))
		response.set_cookie('userId', userId)
		return response



# to be used to call webcrawler with posted data
@application.route('/submit', methods=['POST'])
def launch():
	global userId, url, limit, sType, keyword
	userId = request.cookies.get('userId')
	url = "https://" + request.form['url']
	limit = request.form['limit']
	sType = request.form['type']
	keyword = request.form['keyword']

	#validate url domain and path
	try:
		valid = requests.get(url)
		if valid.status_code != requests.codes.ok:
			flash("'" + url + "' does not exist. Please try again.")
			return redirect(url_for('index'))
	except Exception as e:
		flash("'" + url + "' does not exist. Please try again.")
		return redirect(url_for('index'))


	session['userId']= userId
	session['url'] = url
	session['limit'] = limit
	session['sType'] = sType
	session['keyword'] = keyword

	#adding tracing statement
	print("Value Before Fork: userID=", userId, " url=", url, " limit=", limit, " sType=", sType, "keyword=", keyword)

	return render_template('show_data.html', data=None, url=url, keyword=keyword, type=sType)


@sockets.route('/crawl')
def startCrawl(ws):
	global userId, url, limit, sType, keyword
	userId = session['userId']
	url = session['url']
	limit = session['limit']
	sType = session['sType']
	keyword = session['keyword']
	path = []
	found = False
	early = False

	database = mongo.db.test #access test collection
	postid = database.insert({'userId' : userId, 'url': url, 'limit': limit, 'sType' : sType, 'keyword' : keyword, 'path': path, 'found': found, 'early': early})

	#call crawler, passing socket and db info
	crawler.crawl(ws, url, int(limit), sType, keyword, postid, database)

@application.route('/previous', methods=['POST'])
def getPreviousCrawl():

	#clicked _id from previous crawls list
	docId = request.form['prev']

	test = mongo.db.test #access test collection

	#get data from id
	queryData = test.find_one({'_id' : ObjectId(docId)})

	return render_template('show_data.html', data=queryData['path'], url=queryData['url'], type=queryData['sType'], keyword=queryData['keyword'], found = queryData['found'], early = queryData['early'], docId = docId)


if __name__ == "__main__":
	application.run()
