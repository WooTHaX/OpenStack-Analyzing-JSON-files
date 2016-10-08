from __future__ import division
from flask import Flask, render_template
from tasks import make_celery
import os
import sys
import swiftclient
import pygal
import ast
from collections import Counter
try:
	import json
except ImportError:
	import simplejson as json

# Containers name to retreive documents from
container_name 	= 'tweets'

# Setup connection to swift client containers
config = {'user':os.environ['OS_USERNAME'],
          'key':os.environ['OS_PASSWORD'],
          'tenant_name':os.environ['OS_TENANT_NAME'],
          'authurl':os.environ['OS_AUTH_URL']}
conn = swiftclient.Connection(auth_version=3, **config)

# Create flask app
app = Flask(__name__)
app.config['CELERY_BROKER_URL']='amqp://guest@localhost//'
app.config['CELERY_BACKEND']='rpc://'

# Create cellery worker
celery = make_celery(app)

################# Flask Methods

# Main homepage
#@app.route('/')
#def homepage():
#        return render_template("main.html")

# Method done by the flask app
@app.route('/twitterCount', methods=["GET"])
def twitterCount():
	tweetRetrieveAndCount.delay()
	return "Requesting celery to count pronomen in twitter feed\n"

# Creates bar graph out of json file 
@app.route('/vis', methods=["GET"])
def vis():
        if os.path.isfile("result"):
		bar_chart = pygal.Pie()
		with open("result", 'r') as result_json:
			try:
				#result_dict =  json.loads(result_json)
				result_dict = ast.literal_eval(result_json.read())
				total_count  = sum(result_dict.values()) 
				for key in result_dict:
					#temp = (result_dict[key]/total_count)*100
					bar_chart.add(key, [(result_dict[key]/total_count)*100])
			except Exception, e:
				return(str(e))
		bar_chart.y_title = "Relative usage of pronomen in tweets [%]"
		bar_chart.title = "Usage of different pronumens in tweets"
		bar_chart_data = bar_chart.render_data_uri()
		return render_template("graphing.html", bar_chart_data = bar_chart_data)
	else:
        	return "No result present, run twitter count\n"

################## Celery Methods

# Task that is beeing done by the celery worker
@celery.task(name= 'celery_ex.tweetRetrieveAndCount')
def tweetRetrieveAndCount():
	# Words to count (pronomen in this case)	
	pronomen = {'han': 0, 'hon': 0, 'hen': 0, 
		    'den': 0, 'det': 0, 'denna': 0, 'denne': 0}

	# Goes through each json file in container
	counter_temp = 0;
	for data in conn.get_container(container_name)[1]:
		counter_temp +=1
		if counter_temp == 2:
			break
 		obj_tuple = conn.get_object(container_name, data['name'])

# Only check one json file in container	
#	obj_tuple = conn.get_object(container_name, '05cb5036-2170-401b-947d-68f9191b21c6')

		# Download file (Can not figure out how to skip this step...)
		#with open("temp", 'w') as twitter_text:
		#	twitter_text.write(obj_tuple[1])
		# Open temporary file and count pronomen
		#with open("temp", 'r') as twitter_text:
		currentLine = 0
		for line in obj_tuple[1]:
			print(line)
			currentLine += 1
			if currentLine % 2 == 0:
				continue # Jump to next iteration, skip even empty lines
			try:
				tweet = json.loads(line)
				if 'retweeted_status' not in tweet:
				# Basically dictionary, count of each word --> {'i': 2, 'am': 2}
					countsWord = Counter(tweet['text'].lower().split())
			 		for key in pronomen:
						if key in countsWord:
							pronomen[key] += countsWord[key]
			except ValueError:
				print(ValueError)
			except:
				continue
	print(pronomen)
	# Create json file called result
	with open("result", 'w') as result:
		json.dump(pronomen, result)
	return "End celery tweetRetrieve"

if __name__ == '__main__':
	app.run(host = "0.0.0.0", debug=True)

