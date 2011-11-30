#!/usr/bin/env python
#-*- coding:utf-8 -*-

import smtplib
from email.mime.text import MIMEText
from string import Template
import re
import sys
import os

from ConfigParser import SafeConfigParser

def ask(question, typ, default=None):
	value = None
	while(value == None):
		done = True
		if typ == 'bool':
			choice = re.sub(default, default.upper(), '[yes/no]')
			user_input = raw_input('%s %s :' % (question, choice))
			user_input = user_input.lower()
			if user_input == 'yes' or user_input == '':
				value = 'true'
			elif user_input == 'no':
				value = 'false'
		elif typ == 'string':
			if default == None:
				user_input = raw_input('%s :' % (question))
				if user_input != '':
					value = user_input
			else:
				user_input = raw_input('%s [%s] :' % (question, default))
				if user_input == '':
					value = default
				else:
					value = user_input
		elif typ == 'int':
			user_input = raw_input('%s [%s] :' % (question, default))
			if user_input == '':
				value = default
			else:
				try:
					value = int (user_input)
				except:
					pass
		if value == None:
			print "Please type in one of the choices."
	return value

from email.MIMEBase import MIMEBase
from email import Encoders
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText


class Mail (object):

	def __init__(self, config, files=[]):
		self.smtp_server = config.get('Mail', 'server')
		self.port = config.get('Mail', 'port')
		self.esmtp = config.get('Mail', 'esmtp')
		self.tls = config.get('Mail', 'tls')
		self.user = config.get('Mail', 'user')
		self.password = config.get('Mail', 'password')
		self.mail_from = config.get('Mail', 'email')
		self.files = files

	def connect_smtp(self):
		try:
			self.server = smtplib.SMTP(self.smtp_server, self.port)
			if self.esmtp:
				self.server.ehlo()
				if self.tls: 
					self.server.starttls()
				self.server.ehlo()
			self.server.login(self.user, self.password)
			self.connected = True
		except:
			self.connected = False
			
	def send(self, to, msg):
		for f in self.files:
			part = MIMEBase('application', "octet-stream")
			part.set_payload( open(f,"rb").read() )
			Encoders.encode_base64(part)
			part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(f))
			msg.attach(part)
		self.server.sendmail(self.mail_from, to, msg.as_string())

	def quit(self):
		self.server.quit()

if __name__ == '__main__':
	config = SafeConfigParser()
	config.read('config.txt')
	mail = None
	if not config.has_section('Mail'):
		print 'SMTP Server Settings\n\n'
		config.add_section('Mail')
		value = ask('Server', 'string')
		config.set('Mail', 'server', value)
		value = ask('Port', 'int', '587')
		config.set('Mail', 'port', value)
		value = ask('esmtp', 'bool', 'yes')
		config.set('Mail', 'esmtp', value)
		value = ask('tls', 'bool', 'yes')
		config.set('Mail', 'tls', value)
		value = ask('Whats your login', 'string')
		config.set('Mail', 'user', value)
		value = ask('Whats your password', 'string')
		config.set('Mail', 'password', value)
		value = ask('Whats your email address', 'string', config.get('Mail', 'user'))
		config.set('Mail', 'email', value)
	mail = Mail(config)
	print "try to connect!"
	mail.connect_smtp()
	if mail.connected:
		with open('config.txt', 'wb') as configfile:
			print "success write settings into config!"
			config.write(configfile)
	else:
		print "could not connect with your settings restart with new values!"
		sys.exit(0)

	textfile = "mail.txt"
	if not textfile in os.listdir('.'):
		print "need a file %s in this directory as email-template!" %(textfile)
		sys.exit()

	fp = open(textfile, 'rb')
	plaintext = fp.read()
	keys = re.findall('\$([a-zA-Z]+)', plaintext)
	keys.append('subject')
	keys.append('email')
	import os.path
	import csv
	csv_fn = 'keys.csv'
	if not os.path.exists(csv_fn):
		with open(csv_fn, 'wb') as csv_file:
			writer = csv.DictWriter(csv_file, keys)
			writer.writeheader()
			print "wrote %s file for template data please add some lines!" % (csv_fn)
			print "then restart this programm!"
			sys.exit(0)
	afile = 'attachments.txt'
	if not os.path.exists(afile):
		print 'no %s file found!', (afile)
		print 'If you want attachements create it and place one file location per line in it!'
		value = ask('Should I exit mmailer and create that file empty for you?', 'bool', 'yes')
		if value == 'true':
			open(afile, 'w+')
			sys.exit(0)
	else:
		with open('attachments.txt', 'rb') as afile:
			attachments=[]
			for row in afile:
				attachments.append(row[:-1])
			mail.files=attachments

	with open(csv_fn, 'rb') as csv_file, open(textfile, 'rb') as fp:
		reader = csv.DictReader(csv_file, keys)
		output = Template(plaintext)
		reader.next()
		count = 0
		for row in reader:
			msg_only = output.substitute(row)
			msg = MIMEText(msg_only)
			print msg
			mail_to = row['email']
			print "send to: %s" % mail_to
			print "subject: <%s>" % row['subject']
			approved = ask('Look over the mail is it all right? should I send it for you?', 'bool', 'yes')
			if approved == 'true':
				msg['Subject'] = row['subject']
				msg['From'] = config.get('Mail', 'email')
				msg['To'] = mail_to
				msg2 = MIMEMultipart()
				msg2.attach(msg)
				if not mail.connected:
					mail.connect_smtp()
				mail.send(mail_to, msg2)
				count+=1

		print "did send %s mail[s]!" % (count)
		mail.quit()

