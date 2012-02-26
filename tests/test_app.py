#!/usr/bin/env python
#-*- coding:utf-8 -*-

from os import environ as env
import tempfile
import shutil
import os
from ConfigParser import SafeConfigParser
import getpass
import socket
import sys
import mmailer
from mmailer import MMailer
import subprocess
from subprocess import PIPE, Popen, call
import unittest
from pyDoubles.framework import *
from StringIO import StringIO



class Test_MMailer(object):

	def setup(self):
		self.old_env_home = env['HOME']
		self.temp_dir = tempfile.mkdtemp()
		env['HOME'] = self.temp_dir
		self.config_dir = os.path.join(\
			self.temp_dir, '.config', 'mmailer')
		self.config_path = os.path.join(self.config_dir, 'config')
		self.projects_dir = os.path.join(self.config_dir, 'projects')
		self.last_call = None

	def teardown(self):
		env['HOME'] = self.old_env_home
		shutil.rmtree(self.temp_dir)

	def test_first_start_config_file_created(self):
		mmailer.main()
		assert os.path.isfile(self.config_path)

	def test_first_start_config_file_filled(self):
		mmailer.main()
		uname = getpass.getuser()
		host = socket.gethostname()
		citems = []
		citems.append(('server', host))
		citems.append(('port', '1025'))
		citems.append(('esmtp', 'no'))
		citems.append(('tls', 'no'))
		citems.append(('user', uname))
		citems.append(('password', ''))
		citems.append(('email', uname + "@" + host))
		config = SafeConfigParser()
		config.read(self.config_path)
		assert config.has_section('Mail')
		assert config.items('Mail') == citems

	def test_2nd_start_dont_overwrite_config(self):
		try:
			mmailer.main()
		except:
			pass
		mod_time = os.path.getmtime(self.config_path)
		try:
			mmailer.main()
		except:
			pass
		mod_time2 = os.path.getmtime(self.config_path)
		assert mod_time == mod_time2

	def is_project_selected_in_config(self, target=None):
		config = SafeConfigParser()
		config.read(self.config_path)
		if target != None:
			assert config.has_section('Project')
			assert config.has_option('Project', 'selected')
			assert config.get('Project', 'selected') == target, \
				"<%s> in config should be <%s>" \
					% (config.get('Project', 'selected'), target)
		else:
			assert not config.has_section('Project')

	def test_start_no_arg_right_output(self):
		error_screen = []
		error_screen.append("usage: mmailer.py [-h]")
		error_screen.append( "                  " \
			+"{new,list,select,edit,edit-table,remove,config,send} ...")
		error_screen.append("mmailer.py: error: too few arguments")
		try:
			output = subprocess.check_output('./mmailer.py',
				stderr=subprocess.STDOUT)
		except subprocess.CalledProcessError as cp:
			output = cp.output.splitlines()
		assert output == error_screen, "\n<%s>\nvs\n<%s>" \
			% (output, error_screen)

	def test_list_no_proj(self):
		output = self.mm_list()
		output_target = str("No project availible, create it with"
			+" the new command!\n")
		assert output == output_target

	def mm_list(self):
		return subprocess.check_output(['./mmailer.py', 'list'])

	def mm_remove(self):
		p = subprocess.Popen(['./mmailer.py', 'remove'],\
			stdin=PIPE, stdout=PIPE)
		question = p.communicate('yes')[0]
		assert question == 'Are you shure? [yes/NO] :', question
		try:
			p.communicate()
		except:
			pass
		assert p.poll() == 0
		return


	def mm_select(self, project):
		p = subprocess.call(['./mmailer.py', 'select', project])


	def mm_send(self):
		p = subprocess.Popen(['./mmailer.py', 'send'],\
			stdin=PIPE, stdout=PIPE)
		question = p.communicate('yes')[0]
		try:
			p.communicate()
		except:
			pass
		assert p.poll() == 0
		return

	def mm_create_project(self, name):
		subprocess.call(['./mmailer.py', 'new', name])
		return os.path.join(self.projects_dir, name)

	def test_command_list_filled(self):
		"adds some projects and checks output of the command <list>"
		prj_added = []
		for p in ['B-Project', 'A-Project', 'C-Project']:
			self.mm_create_project(p)
			prj_added.append(p)
			prj_added.sort()
			pa_lines=''
			for pa in prj_added:
				if pa == 'B-Project':
					pa_lines += "%s *\n" % (pa)
				else:
					pa_lines += "%s\n" % (pa)
			prj_str = 'Projects:\n---------\n%s\n' % (pa_lines)
			assert self.mm_list() == prj_str, '\n' + self.mm_list()+ prj_str

	def test_command_new_works(self):
		list_projects = []
		list_projects.append('Project "Test" created!')
		proj_dir = self.mm_create_project('Test')
		assert os.path.exists(proj_dir)
		assert os.path.isdir(proj_dir)
		self.is_project_selected_in_config('Test')

	def test_command_new_2nd_start_dont_override_proj(self):
		proj_dir = self.mm_create_project('project_test')
		mod_time = os.path.getmtime(proj_dir)
		self.mm_create_project('project_test')
		mod_time2 = os.path.getmtime(proj_dir)
		assert mod_time == mod_time2

	def test_command_remove_proj_dir(self):
		'checks if the remove command removes (only) the proj dir'
		proj1_dir = self.mm_create_project('Test')
		proj2_dir = self.mm_create_project('Test2')
		self.mm_remove()
		assert not os.path.exists(proj1_dir), proj1_dir
		assert os.path.exists(proj2_dir)

	def test_command_remove_updates_selected_proj(self):
		projects = ['B-Project', 'C-Project', 'A-Project']
		for p in projects:
			self.mm_create_project(p)
		self.is_project_selected_in_config(projects[0])
		self.mm_remove()
		self.is_project_selected_in_config(projects[2])
		self.mm_remove()
		self.is_project_selected_in_config(projects[1])
		self.mm_remove()
		self.is_project_selected_in_config(None)

	def save_call(self, call_dict):
		self.last_call = call_dict

	def test_command_edit(self):
		proj_dir = self.mm_create_project('Test')
		env['EDITOR'] = 'gedit'
		sys.argv = ['mmailer', 'edit']
		subprocess_call_save = subprocess.call
		subprocess.call = self.save_call
		assert mmailer.main(sys.argv) == 0
		subprocess.call = subprocess_call_save
		files = ['mail.txt', 'subject.txt', 'attachments.txt']
		abs_files = []
		for f in files:
			abs_file = os.path.join(proj_dir, f)
			#assert os.path.isfile(abs_file)
			abs_files.append(abs_file)
		assert self.last_call == ['gedit', abs_files[0], \
			abs_files[1], abs_files[2]], self.last_call

	def create_with_sample_files(self, proj_dir, files=None):
		if files == None:
			files = ['mail.txt', 'subject.txt']
		for f in files:
			shutil.copy(os.path.join('tests','samples', f), proj_dir)


	def test_command_edit_table(self):
		proj_dir = self.mm_create_project('Test')
		self.create_with_sample_files(proj_dir)
		env['EDITOR'] = 'gedit'
		sys.argv = ['mmailer', 'edit-table']
		subprocess_call_save = subprocess.call
		subprocess.call = self.save_call
		abs_file = os.path.join(proj_dir, 'keys.csv')
		assert mmailer.main(sys.argv) == 0
		subprocess.call = subprocess_call_save
		assert os.path.exists(abs_file), os.path.join(proj_dir, 'keys.txt')
		assert self.last_call == ['gedit', abs_file], self.last_call
		import filecmp
		target = os.path.join('tests','samples', 'keys-empty.csv')
		assert filecmp.cmp(target, abs_file)

	def test_command_select(self):
		projects = ['A-Project', 'B-Project', 'C-Project']
		for p in projects:
			self.mm_create_project(p)
		self.is_project_selected_in_config(projects[0])
		self.mm_select('C-Project')
		self.is_project_selected_in_config(projects[2])

	def test_command_select_non_existend(self):
		projects = ['A-Project', 'B-Project']
		for p in projects:
			self.mm_create_project(p)
		self.is_project_selected_in_config(projects[0])
		self.mm_select('D-Project')
		self.is_project_selected_in_config(projects[0])



	def test_command_config_not_valid_smtp(self):
		questions = ['SMTP Server Settings', '\n\n\n', \
				'Server :', 'Port [587] :', 'esmtp [YES/no] :', \
				'tls [YES/no] :', 'Whats your login :',  \
				'Whats your password :', 'Whats your email address [x] :', \
				'try to connect!\n', \
				'could not connect - restart and try again!\n']
		answers = ['localhost', '0', '', '', 'x', 'x', 'x']
		sys.stdin = x_in = StringIO('\n'.join(answers))
		sys.stdout = x_out = StringIO()
		m = MMailer()
		mod_time = os.path.getmtime(self.config_path)
		m.command_config(args=['mmailer', '	config'])
		mod_time2 = os.path.getmtime(self.config_path)
		config_changed = not mod_time == mod_time2
		sys.stdin = sys.__stdin__
		sys.stdout = sys.__stdout__
		assert "".join(questions) == x_out.getvalue(), \
			'\n[%s] != \n[%s]' % ("".join(questions), x_out.getvalue())
		assert config_changed == False


# should implement the python internal smtp server,
# and with the following it should be tested

#	def test_command_config(self):
#		questions = ['SMTP Server Settings', '\n\n\n', \
#				'Server :', 'Port [587] :', 'esmtp [YES/no] :', \
#				'tls [YES/no] :', 'Whats your login :',  \
#				'Whats your password :', 'Whats your email address [john@localhost] :', \
#				'try to connect!\n', \
#				'could not connect - restart and try again!\n']
#		answers = ['localhost', '\n', '\n', '\n', 'john', '\n', '\n']
#		sys.stdin = x_in = StringIO('\n'.join(answers))
#		sys.stdout = x_out = StringIO()
#		m = MMailer()
#		mod_time = os.path.getmtime(self.config_path)
#		m.command_config(args=['mmailer', '	config'])
#		mod_time2 = os.path.getmtime(self.config_path)
#		config_changed = not mod_time == mod_time2
#		sys.stdin = sys.__stdin__
#		sys.stdout = sys.__stdout__
#		assert "".join(questions) == x_out.getvalue(), \
#			'\n[%s] != \n[%s]' % ("".join(questions), x_out.getvalue())
#		assert config_changed == False


# with the internal python smtp and a pop3-server I should test
# the send command here:

#	def test_command_send(self):
#		files = ['mail.txt', 'subject.txt', 'keys.csv']
#		proj_dir = self.mm_create_project('Test')
#		self.create_with_sample_files(proj_dir, files)
#		sample_path = os.path.abspath(os.path.join('.','tests', 'samples'))
#		with open(os.path.join(proj_dir, 'attachments.txt'), 'w') as afile:
#			attach1 = os.path.join(sample_path, 'attach_bin.gz')
#			attach2 = os.path.join(sample_path, 'attach_ascii.txt')
#			afile.write('%s\n%s\n' % (attach1, attach2))

#		abs_file = os.path.join(proj_dir, 'keys.csv')
#		self.mm_send()


