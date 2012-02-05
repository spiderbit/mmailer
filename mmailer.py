#!/usr/bin/env python
#-*- coding:utf-8 -*-

from string import Template
import re
import sys
import os
import smtplib

from ConfigParser import SafeConfigParser
from email.MIMEBase import MIMEBase
from email import Encoders
from email.MIMEMultipart import MIMEMultipart
from smtplib import SMTP
from email.MIMEText import MIMEText
from email.Header import Header
from email.Utils import parseaddr, formataddr


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


class Mail (object):

	def __init__(self, config, files=[]):
		self.smtp_server = config.get('Mail', 'server')
		self.port = config.get('Mail', 'port')
		self.esmtp = config.getboolean('Mail', 'esmtp')
		self.tls = config.getboolean('Mail', 'tls')
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

	def quit(self):
		self.server.quit()



	def send(self, sender, recipient, subject, body):
		"""Send an email.

		All arguments should be Unicode strings (plain ASCII works as well).

		Only the real name part of sender and recipient addresses may contain
		non-ASCII characters.

		The email will be properly MIME encoded and delivered though SMTP to
		localhost port 25.  This is easy to change if you want something different.

		The charset of the email will be the first one out of US-ASCII, ISO-8859-1
		and UTF-8 that can represent all the characters occurring in the email.
		"""

		# Header class is smart enough to try US-ASCII, then the charset we
		# provide, then fall back to UTF-8.
		header_charset = 'ISO-8859-1'

		# We must choose the body charset manually
		for body_charset in 'US-ASCII', 'ISO-8859-1', 'UTF-8':
			try:
				body.encode(body_charset)
			except UnicodeError:
				pass
			else:
				break

		# Split real name (which is optional) and email address parts
		sender_name, sender_addr = parseaddr(sender)
		recipient_name, recipient_addr = parseaddr(recipient)

		# We must always pass Unicode strings to Header, otherwise it will
		# use RFC 2047 encoding even on plain ASCII strings.
		sender_name = str(Header(unicode(sender_name), header_charset))
		recipient_name = str(Header(unicode(recipient_name), header_charset))

		# Make sure email addresses do not contain non-ASCII characters
		sender_addr = sender_addr.encode('ascii')
		recipient_addr = recipient_addr.encode('ascii')

		# Create the message ('plain' stands for Content-Type: text/plain)
		msg = MIMEMultipart()
		body_msg = MIMEText(body.encode(body_charset), 'plain', body_charset)
		msg['From'] = formataddr((sender_name, sender_addr))
		msg['To'] = formataddr((recipient_name, recipient_addr))
		msg['Subject'] = Header(unicode(subject), header_charset)
		msg["Content-type"] = "text/html;charset=utf-8"
		msg.attach(body_msg)
		for f in self.files:
			part = MIMEBase('application', "octet-stream")
			part.set_payload( open(f,"rb").read() )
			Encoders.encode_base64(part)
			part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(f))
			msg.attach(part)
		# Send the message via SMTP
		self.server.sendmail(sender, recipient, msg.as_string())


def main():
	config = SafeConfigParser()
	config.read('config.txt')
	mail = None
	global os
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
	template_files = dict()
	template_files['mail'] = "mail.txt"
	template_files['subject'] = "subject.txt"
	keys = []
	for k,v in template_files.iteritems():
		if not v in os.listdir('.'):
			print "need a file %s in this directory as %s-template!" %(v,k)
			sys.exit()
		else:
			fp = open(v, 'rb')
			plaintext = fp.read()
			tmp_keys = re.findall('\$([a-zA-Z]+)', plaintext)
			keys.extend(tmp_keys)
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

	with open(csv_fn, 'rb') as csv_file, open(template_files['mail'], 'rb') as mail_template,\
			open(template_files['subject'], 'rb') as subject_template:
		reader = csv.DictReader(csv_file, keys)
		output = Template(mail_template.read())
		reader.next()
		output_subject = Template(subject_template.readline()[:-1])
		count = 0
		for row in reader:
			msg_only = output.substitute(row)
			subject = unicode(output_subject.substitute(row), encoding='UTF-8')
			print msg_only
			mail_to = row['email']
			print "send to: %s" % mail_to
			print "subject: <%s>" % subject
			approved = ask('Look over the mail is it all right? should I send it for you?', 'bool', 'yes')
			if approved == 'true':
				if not mail.connected:
					mail.connect_smtp()
				body = unicode(msg_only, encoding='UTF-8')
				recipient = unicode(mail_to, encoding='UTF-8')
				sender = unicode(config.get('Mail', 'email'), encoding='UTF-8')
				mail.send(sender, recipient, subject, body)
				count+=1

		print "did send %s mail[s]!" % (count)
		mail.quit()


if __name__ == '__main__':
	sys.exit(main())


