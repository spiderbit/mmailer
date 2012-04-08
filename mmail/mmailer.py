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
import subprocess
import os.path
import csv
import getpass
import socket
from os import environ as env
import argparse
import shutil

def ask(question, typ, default=None):
	value = None
	while(value == None):
		done = True
		if typ == 'bool':
			choice = re.sub(default, default.upper(), '[yes/no]')
			user_input = raw_input('%s %s :' % (question, choice))
			user_input = user_input.lower()
			if user_input == 'yes' or user_input == '':
				value = True
			elif user_input == 'no':
				value = False
		elif typ == 'string':
			if default == None or default == '':
				user_input = raw_input('%s :' % (question))
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


class SMTP(object):
	def __init__(self):
		self.cm = ConfigManager()
		self.load_config()

	def load_config(self):
		config = self.cm.config
		self.smtp_server = config.get('Mail', 'server')
		self.port = config.get('Mail', 'port')
		self.esmtp = config.getboolean('Mail', 'esmtp')
		self.tls = config.getboolean('Mail', 'tls')
		self.user = config.get('Mail', 'user')
		self.password = config.get('Mail', 'password')
		self.mail_from = config.get('Mail', 'email')
		self.connected = False

	def connect(self):
		try:
			self.server = smtplib.SMTP(self.smtp_server, self.port)
			if self.esmtp:
				self.server.ehlo()
			if self.tls:
				self.server.starttls()
			if self.user != '':
				self.server.login(self.user, self.password)
			self.connected = True
		except:
			self.connected = False


	def ask_settings(self):
		# should be a mmailer config method
		home = env['HOME']
		config = self.cm.config
		mail = None
		print 'SMTP Server Settings\n\n'
		value = str(ask('Server', 'string'))
		self.cm.config.set('Mail', 'server', value)
		value = str(ask('Port', 'int', '587'))
		self.cm.config.set('Mail', 'port', value)
		value = str(ask('esmtp', 'bool', 'yes'))
		self.cm.config.set('Mail', 'esmtp', value)
		value = str(ask('tls', 'bool', 'yes'))
		self.cm.config.set('Mail', 'tls', value)
		value = str(ask('Whats your login', 'string'))
		self.cm.config.set('Mail', 'user', value)
		value = str(ask('Whats your password', 'string'))
		self.cm.config.set('Mail', 'password', value)
		value = str(ask('Whats your email address',
			'string', config.get('Mail', 'user')))
		self.cm.config.set('Mail', 'email', value)
		self.load_config()
		print "try to connect!"
		self.connect()
		mail_txt= "Test mail from the tool mmailer" \
			" (https://github.com/spiderbit/mmailer) tool to see if the" \
			" given smtp server works"
		tested = True
		try:
			self.server.sendmail(self.mail_from, self.mail_from, mail_txt)
		except:
			tested = False
		if tested:
			self.cm.write()
		else:
			print ("could not connect - restart and try again!")


	def quit(self):
		if self.connected:
			self.server.quit()


class Mail (object):

	def __init__(self, files=[], smtp=None):
		self.files = files
		self.smtp = smtp
		self.approved = False


	def show(self):
		# We must choose the body charset manually
		for body_charset in 'US-ASCII', 'ISO-8859-1', 'UTF-8':
			try:
				self.body.encode(body_charset)
			except UnicodeError:
				pass
			else:
				break
		body_msg = MIMEText(self.body.encode(body_charset), \
			'plain', body_charset)
		print self.body
		print "send to: %s" % self.recipient
		print "subject: <%s>" % self.subject


	def send(self):
		"""Send an email.

		All arguments should be Unicode strings (plain ASCII works as well).

		Only the real name part of sender and recipient addresses may contain
		non-ASCII characters.

		The email will be properly MIME encoded and delivered though SMTP to
		localhost port 25.  This is easy to change if you want something different.

		The charset of the email will be the first one out of US-ASCII, ISO-8859-1
		and UTF-8 that can represent all the characters occurring in the email.
		"""

		if not self.approved:
			return False

		# Header class is smart enough to try US-ASCII, then the charset we
		# provide, then fall back to UTF-8.
		header_charset = 'ISO-8859-1'

		# We must choose the body charset manually
		for body_charset in 'US-ASCII', 'ISO-8859-1', 'UTF-8':
			try:
				self.body.encode(body_charset)
			except UnicodeError:
				pass
			else:
				break

		# Split real name (which is optional) and email address parts
		sender_name, sender_addr = parseaddr(self.sender)
		recipient_name, recipient_addr = parseaddr(self.recipient)

		# We must always pass Unicode strings to Header, otherwise it will
		# use RFC 2047 encoding even on plain ASCII strings.
		sender_name = str(Header(unicode(sender_name), header_charset))
		recipient_name = str(Header(unicode(recipient_name), header_charset))

		# Make sure email addresses do not contain non-ASCII characters
		sender_addr = sender_addr.encode('ascii')
		recipient_addr = recipient_addr.encode('ascii')

		# Create the message ('plain' stands for Content-Type: text/plain)
		msg = MIMEMultipart()
		body_msg = MIMEText(self.body.encode(body_charset), 'plain', body_charset)
		msg['From'] = formataddr((sender_name, sender_addr))
		msg['To'] = formataddr((recipient_name, recipient_addr))
		msg['Subject'] = Header(unicode(self.subject), header_charset)
		msg["Content-type"] = "text/html;charset=utf-8"
		msg.attach(body_msg)
		for f in self.files:
			part = MIMEBase('application', "octet-stream")
			part.set_payload( open(f,"rb").read() )
			Encoders.encode_base64(part)
			part.add_header('Content-Disposition', \
				'attachment; filename="%s"' % os.path.basename(f))
			msg.attach(part)
		# Send the message via SMTP
		self.smtp.connect()
		self.smtp.server.sendmail(self.sender, self.recipient, msg.as_string())
		return True



class ConfigManager (object):

	def __init__(self):
		uname = getpass.getuser()
		host = socket.gethostname()
		home = env['HOME']
		self.config_dir = os.path.join(home, '.config', 'mmailer')
		self.config_path = os.path.join(self.config_dir, 'config')
		config = self.config = SafeConfigParser()
		if os.path.isfile(self.config_path):
			self.read()
		else:
			config.add_section('Mail')
			config.set('Mail', 'server', host)
			config.set('Mail', 'port', '1025')
			config.set('Mail', 'esmtp', 'no')
			config.set('Mail', 'tls', 'no')
			config.set('Mail', 'user', uname)
			config.set('Mail', 'password', '')
			config.set('Mail', 'email', uname + "@" + host)
			self.write()

	def write(self):
		if not os.path.exists(self.config_dir):
			os.makedirs(self.config_dir)
		with open(self.config_path, 'wb') as config_file:
			self.config.write(config_file)

	def read(self):
		self.config.read(self.config_path)

	def set_active_project(self, name):
		if not self.config.has_section('Project'):
			self.config.add_section('Project')
		self.config.set('Project', 'selected', name)
		self.write()

	def remove_section_project(self):
		if self.config.has_section('Project'):
			self.config.remove_section('Project')
		self.write()

	def get_active_project(self):
		if self.config.has_section('Project'):
			return self.config.get('Project', 'selected')
		return None



class Project (object):

	def __init__(self, name):
		self.name = name
		home = env['HOME']
		config_dir = os.path.join(home, '.config', 'mmailer')
		self.projects_dir = os.path.join(config_dir, 'projects')
		self.proj_dir = os.path.join(self.projects_dir, name)
		self.attachments=[]
		self.template_files=dict()
		self.template_files['mail'] = \
			os.path.join(self.proj_dir, 'mail.txt')
		self.template_files['subject'] = \
			os.path.join(self.proj_dir, 'subject.txt')
		self.keys = []
		self.cm = ConfigManager()
		self.mails = []

	def create(self):
		if not os.path.exists(self.proj_dir):
			os.makedirs(self.proj_dir)

	def create_files(self):
		sys.exit("code commented out for reinspection")
		# overrides the files at the moment
		# maybe not neaded for edit command anyway
		for f in self.files():
			p = open(f, 'w')
			p.write('')
			p.close()

	def files(self):
		files = ['mail.txt', 'subject.txt', 'attachments.txt']
		abs_files = []
		for f in files:
			abs_files.append(os.path.join(self.proj_dir, f))
		return abs_files

	def substitude_file(self):
		sfile = os.path.join(self.proj_dir, 'keys.csv')
		return sfile

	def remove(self):
		shutil.rmtree(self.proj_dir)

	def load_keys(self):
		template_files = self.template_files
		for k,v in template_files.iteritems():
			#if not v in os.listdir('.'):
			#	print "need a file %s in this directory as %s-template!" %(v,k)
			#	sys.exit()
			#else:
			fp = open(v, 'rb')
			plaintext = fp.read()
			tmp_keys = re.findall('\$([a-zA-Z_]+)', plaintext)
			self.keys.extend(tmp_keys)
		self.keys = list(set(self.keys)) # to remove double entries
		self.keys.append('email')

	def create_table(self):
		abs_files = self.files()
		self.load_keys()
		keys = self.keys
		csv_fn = os.path.join(self.proj_dir, 'keys.csv')
		if not os.path.exists(csv_fn):
			with open(csv_fn, 'wb') as csv_file:
				writer = csv.DictWriter(csv_file, keys)
				writer.writeheader()
		#afile = os.path.join(self.proj_dir, 'attachments.txt')

		#if not os.path.exists(afile):
		#	print 'no %s file found!', (afile)
		#	print ("If you want attachements create it "
		#		"and place one file location per line in it!")
		#	value = ask('Should I exit mmailer and create'
		#		' that file empty for you?', 'bool', 'yes')
		#	if value == 'true':
		#		open(afile, 'w+')
		#		sys.exit(0)
		#else:

	def load_attachments(self):
		afile = os.path.join(self.proj_dir,'attachments.txt')
		with open(afile, 'rb') as afile:
			for row in afile:
				if os.path.isfile(row[:-1]):
					self.attachments.append(row[:-1])
				else:
					sys.exit("one of your attachments \
					dont exist or is no file: <%s>" % (row[:-1]))
		return

	def send(self):
		self.load_keys()
		keys = self.keys
		config = self.cm.config
		self.load_attachments()
		smtp = SMTP()
		with open(self.substitude_file(), 'rb') as csv_file, \
		open(self.template_files['mail'], 'rb') as mail_template,\
		open(self.template_files['subject'], 'rb') as subject_template:
			reader = csv.DictReader(csv_file, keys)
			output = Template(mail_template.read())
			reader.next()
			output_subject = Template(subject_template.readline()[:-1])
			count = 0

			for row in reader:
				mail = Mail(self.attachments, smtp)
				msg_only = output.substitute(row)
				mail.subject = unicode(output_subject.substitute(row), \
					encoding='UTF-8')
				mail_to = row['email']
				mail.body = unicode(msg_only, encoding='UTF-8')
				mail.recipient = unicode(mail_to, encoding='UTF-8')
				mail.sender = unicode(config.get('Mail', 'email'), \
					encoding='UTF-8')
				mail.show()
				mail.approved = ask('Look over the mail is it all right?'\
					' should I send it for you?', 'bool', 'yes')
				self.mails.append(mail)

		smtp.connect()
		for mail in self.mails:
			if mail.send():
				count+=1
		print "did send %s mail[s]!" % (count)
		smtp.quit()

class ProjectList (object):

	def __init__(self):
		self.projects = dict()
		self.cm = ConfigManager()
		home = env['HOME']
		config_dir = os.path.join(home, '.config', 'mmailer')
		self.projects_dir = os.path.join(config_dir, 'projects')
		if not os.path.exists(self.projects_dir):
			os.makedirs(self.projects_dir)
		self.search()

	def projects_sorted(self):
		keylist = self.projects.keys()
		keylist.sort()
		return keylist

	def search(self):
		files = os.listdir(self.projects_dir)
		for f in files:
			if os.path.isdir(os.path.join(self.projects_dir, f)):
				self.projects[f] = Project(f)

	def add_project(self, name):
		if len(self.projects) == 0:
			self.cm.set_active_project(name)
		p = Project(name)
		p.create()
		self.projects[name] = p

	def remove(self, name):
		self.projects[name].remove()
		del self.projects[name]
		if len (self.projects) > 0:
			new_default = self.projects_sorted()[0]
			self.cm.set_active_project(new_default)
		else:
			self.cm.remove_section_project()

	def get_active_project(self):
		return self.cm.get_active_project()


	def set_active_project(self, name):
		return self.cm.set_active_project(name)


class MMailer (object):

	def __init__(self):
		self.cm = ConfigManager()

	def command_new(self, args):
		name = args.proj_name
		pl = ProjectList()
		if not name in pl.projects.keys():
			pl.add_project(name)
		return

	def command_list(self, args):
		pl = ProjectList()
		if len(pl.projects) == 0:
			print "No project availible, create it with the new command!"
		else:
			p_names = pl.projects_sorted()
			pa_lines=''
			for pa in p_names:
				selected_prj = pl.cm.config.get('Project', 'selected')
				if pa == selected_prj:
					pa_lines += "%s *\n" % (pa)
				else:
					pa_lines += "%s\n" % (pa)
			prj_str = 'Projects:\n---------\n%s' % (pa_lines)
			print prj_str

	def command_edit(self, args):
		pl = ProjectList()
		active_project = pl.get_active_project()
		if active_project != None:
			p = pl.projects[active_project]
			#p.create_files()
			retvalue = subprocess.call( \
				[env['EDITOR']] + p.files())
			if retvalue == 0:
				pass
		return

	def command_edit_table(self, args):
		pl = ProjectList()
		active_project = pl.get_active_project()
		if active_project != None:
			p = pl.projects[active_project]
			p.create_table()
			retvalue = subprocess.call(
				[env['EDITOR'], p.substitude_file()])
			if retvalue == 0:
				pass
		return

	def command_remove(self, args):
		pl = ProjectList()
		active_project = pl.get_active_project()
		if active_project != None:
			confirmed = ask('Are you shure?', 'bool', 'no')
			if confirmed:
				pl.remove(active_project)
		return

	def command_select(self, args):
		name = args.proj_name
		pl = ProjectList()
		if name in pl.projects.keys():
			pl.set_active_project(name)
		return

	def command_send(self, args):
		pl = ProjectList()
		active_project = pl.get_active_project()
		if active_project != None:
			p = pl.projects[active_project]
			p.send()


	def command_config(self, args):
		smtp = SMTP()
		smtp.ask_settings()

	def command_version(self, args):
		from _version import get_versions
		print get_versions()['version']

def args_config():
	m = MMailer()
	parser = argparse.ArgumentParser(
		description='Serial mail managing tool.')
	subparsers = parser.add_subparsers()
	new_parser = subparsers.add_parser('new')
	new_parser.add_argument('proj_name')
	new_parser.set_defaults(func=m.command_new)
	list_parser = subparsers.add_parser('list')
	list_parser.set_defaults(func=m.command_list)
	version_parser = subparsers.add_parser('version')
	version_parser.set_defaults(func=m.command_version)
	select_parser = subparsers.add_parser('select')
	select_parser.add_argument('proj_name')
	select_parser.set_defaults(func=m.command_select)
	edit_parser = subparsers.add_parser('edit')
	edit_parser.set_defaults(func=m.command_edit)
	edit_table_parser = subparsers.add_parser('edit-table')
	edit_table_parser.set_defaults(func=m.command_edit_table)
	remove_parser = subparsers.add_parser('remove')
	remove_parser.set_defaults(func=m.command_remove)
	config_parser = subparsers.add_parser('config')
	config_parser.set_defaults(func=m.command_config)
	send_parser = subparsers.add_parser('send')
	send_parser.set_defaults(func=m.command_send)
	new_parser.description = "creates a new project"
	version_parser.description = "prints out the version of mmailer"
	list_parser.description = "lists all projects"
	select_parser.description = "selects a project"
	edit_parser.description = "edits the project files"
	edit_table_parser.description = "generates a table where each line \
		you fill will create a mail"
	remove_parser.description = "removes the active project"
	config_parser.description = "asks you for you smtp-server settings"
	send_parser.description = "sends the emails generated from your \
		current project"
	args = parser.parse_args(sys.argv[1:])
	if 'func' in args:
		args.func(args)


def main(args=None):

	args_config()
	return 0



if __name__ == '__main__':
	sys.exit(main(args=sys.argv))
