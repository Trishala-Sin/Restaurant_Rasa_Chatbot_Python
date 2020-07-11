from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json
import re
import urllib3
from rasa_sdk import Action
from rasa_sdk.events import SlotSet

urllib3.disable_warnings()

import smtplib
import os
import re
import requests

import json
import pandas as pd
from threading import Thread
from flask import Flask
from flask_mail import Mail, Message

import zomatopy


# Action search
class ActionSearchRestaurants(Action):
	def name(self):
		return 'action_search_restaurants'

	def run(self, dispatcher, tracker, domain):
		config = {"user_key": "f4924dc9ad672ee8c4f8c84743301af5"}
		zomato = zomatopy.initialize_app(config)
		loc = tracker.get_slot('location')
		cuisine = tracker.get_slot('cuisine')
		location_detail = zomato.get_location(loc, 1)
		d1 = json.loads(location_detail)
		lat = d1["location_suggestions"][0]["latitude"]
		lon = d1["location_suggestions"][0]["longitude"]
		cuisines_dict = {'bakery': 5, 'chinese': 25, 'cafe': 30, 'italian': 55, 'biryani': 7, 'north indian': 50,
						 'south indian': 85}
		results = zomato.restaurant_search("", lat, lon, str(cuisines_dict.get(cuisine)), 5)
		d = json.loads(results)
		response = ""
		if d['results_found'] == 0:
			response = "no results"
		else:
			for restaurant in d['restaurants']:
				response = response + "Found " + restaurant['restaurant']['name'] + " in " + restaurant['restaurant']['location']['address'] + "\n"

		dispatcher.utter_message("-----" + response)
		return [SlotSet('location', loc)]


class VerifyLocation(Action):
	TIER_1 = []
	TIER_2 = []

	def __init__(self):
		self.TIER_1 = ['ahmedabad', 'bangalore', 'chennai', 'delhi', 'hyderabad', 'kolkata', 'mumbai', 'pune']
		self.TIER_2 = ['agra', 'ajmer', 'aligarh', 'amravati', 'amritsar', 'asansol', 'aurangabad', 'bareilly',
					   'belgaum',
					   'bhavnagar', 'bhiwandi', 'bhopal', 'bhubaneswar', 'bikaner', 'bilaspur', 'bokaro steel city',
					   'chandigarh',
					   'coimbatore', 'cuttack', 'dehradun', 'dhanbad', 'bhilai', 'durgapur', 'erode', 'faridabad',
					   'firozabad',
					   'ghaziabad', 'gorakhpur', 'gulbarga', 'guntur', 'gwalior', 'gurgaon', 'guwahati', 'hamirpur',
					   'hubli–dharwad',
					   'indore', 'jabalpur', 'jaipur', 'jalandhar', 'jammu', 'jamnagar', 'jamshedpur', 'jhansi',
					   'jodhpur',
					   'kakinada', 'kannur', 'kanpur', 'kochi', 'kolhapur', 'kollam', 'kozhikode', 'kurnool',
					   'ludhiana', 'lucknow',
					   'madurai', 'malappuram', 'mathura', 'goa', 'mangalore', 'meerut', 'moradabad', 'mysore',
					   'nagpur', 'nanded',
					   'nashik', 'nellore', 'noida', 'patna', 'pondicherry', 'purulia', 'prayagraj', 'raipur', 'rajkot',
					   'rajahmundry', 'ranchi', 'rourkela', 'salem', 'sangli', 'shimla', 'siliguri', 'solapur',
					   'srinagar', 'surat',
					   'thiruvananthapuram', 'thrissur', 'tiruchirappalli', 'tiruppur', 'ujjain', 'bijapur', 'vadodara',
					   'varanasi',
					   'vasai-virar city', 'vijayawada', 'visakhapatnam', 'vellore', 'warangal']

	def name(self):
		return "verify_location"

	def run(self, dispatcher, tracker, domain):
		loc = tracker.get_slot('location')

		if not (self.verify_location(loc)):
			dispatcher.utter_message("Sorry, we do not operate in " + loc + " yet. Please try some other city.")
			return [SlotSet('location', None), SlotSet("location_ok", False)]
		else:
			return [SlotSet('location', loc), SlotSet("location_ok", True)]

	def verify_location(self, loc):
		return loc.lower() in self.TIER_1 or loc.lower() in self.TIER_2
		# return loc.str.lower() in self.TIER_1 or loc.str.lower() in self.TIER_2

class ActionRestarted(Action):
	def name(self):
		return 'action_restart'

	def run(self, dispatcher, tracker, domain):
		return[Restarted()]

class ActionSlotReset(Action):
	def name(self):
		return 'action_slot_reset'

	def run(self, dispatcher, tracker, domain):
		return[AllSlotsReset()]

class ActionValidateEmail(Action):
	def name(self):
		return 'action_validate_email'

	def run(self, dispatcher, tracker, domain):
		pattern = "(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
		email_check = tracker.get_slot('email')
		if email_check is not None:
			if re.search("(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", email_check):
				return [SlotSet('email', email_check)]
			else:
				dispatcher.utter_message("Sorry this is not a valid email. please check for typing errors")
				return [SlotSet('email', None)]
		else:
			dispatcher.utter_message(
				"Sorry I could not understand the email address which you provided? Please provide again")
			return [SlotSet('email', None)]


def mail_config():
	gmail_user = "rakesh.sit045@gmail.com"
	gmail_pwd = "Rakeshkumar@06184"  # Gmail Password
	mail_settings = {

		"MAIL_SERVER": 'smtp.gmail.com',
		"MAIL_PORT": 465,
		"MAIL_USE_TLS": False,
		"MAIL_USE_SSL": True,
		"MAIL_USERNAME": gmail_user,
		"MAIL_PASSWORD": gmail_pwd,

	}
	return mail_settings


app = Flask(__name__)
app.config.update(mail_config())
mail = Mail(app)


def send_async_email(app, recipient, response):
	with app.app_context():
		msg = Message(subject="Restaurant Details", sender="rakesh.sit045@gmail.com", recipients=[recipient])
		msg.html = u'<h2>Foodie has found few restaurants for you:</h2>'
		mail.send(msg)


def send_email(recipient, response):
	thr = Thread(target=send_async_email, args=[app, recipient, response])
	thr.start()


class SendMail(Action):
	def name(self):
		return 'action_send_mail'

	def run(self, dispatcher, tracker, domain):
		recipient = tracker.get_slot('email')

		# top10 = restaurants.head(10)
		top10 = "testing 45...."
		send_email(recipient, top10)

		dispatcher.utter_message("Have a great day! Mail is sent")
