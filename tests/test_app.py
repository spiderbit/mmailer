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
from mmail.mmailer import MMailer
import subprocess
from subprocess import PIPE, Popen, call
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

	def get_default_config_scheme(self):
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
		return citems

	def get_testserver_config_scheme(self):
		uname = getpass.getuser()
		host = socket.gethostname()
		citems = []
		citems.append(('server', 'localhost'))
		citems.append(('port', '1555'))
		citems.append(('esmtp', 'False'))
		citems.append(('tls', 'False'))
		citems.append(('user', ''))
		citems.append(('password', ''))
		citems.append(('email', 'x' + "@" + 'localhost'))
		return citems

	def test_first_start_config_file_filled(self):
		mmailer.main()
		citems = self.get_default_config_scheme()
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
		error_screen.append("usage: mmailer [-h]")
		error_screen.append("               " \
			+ "{new,list,version,select,edit,edit-table,remove,config,send}")
		error_screen.append("               ...")
		error_screen.append("mmailer: error: too few arguments")
		try:
			output = subprocess.check_output('./mmailer',
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
		return subprocess.check_output(['./mmailer', 'list'])

	def mm_remove(self):
		p = subprocess.Popen(['./mmailer', 'remove'],\
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
		p = subprocess.call(['./mmailer', 'select', project])


	def mm_send(self):
		p = subprocess.Popen(['./mmailer', 'send'],\
			stdin=PIPE, stdout=PIPE)
		question = p.communicate('yes')[0]
		try:
			p.communicate()
		except:
			pass
		assert p.poll() == 0
		return

	def mm_create_project(self, name):
		subprocess.call(['./mmailer', 'new', name])
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

	def create_with_sample_files(self, sample_dir, proj_dir, files=None):
		if files == None:
			files = ['mail.txt', 'subject.txt']
		for f in files:
			shutil.copy(os.path.join('tests','samples', sample_dir, f), proj_dir)


	def test_command_edit_table(self):
		proj_dir = self.mm_create_project('Test')
		self.create_with_sample_files("", proj_dir)
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

	def mm_config_fill(self, port=1555):
		questions = ['SMTP Server Settings', '\n\n\n', \
				'Server :', 'Port [587] :', 'esmtp [YES/no] :', \
				'tls [YES/no] :', 'Whats your login :',  \
				'Whats your password :', 'Whats your email address :', \
				'try to connect!\n']
		answers = ['localhost', str(port), 'no', 'no', '', '', 'x@localhost']
		sys.stdin = x_in = StringIO('\n'.join(answers))
		sys.stdout = x_out = StringIO()
		m = MMailer()
		mod_time = os.path.getmtime(self.config_path)
		m.command_config(args=['mmailer', '	config'])
		mod_time2 = os.path.getmtime(self.config_path)
		config_changed = not (mod_time == mod_time2)
		sys.stdin = sys.__stdin__
		sys.stdout = sys.__stdout__
		#assert "".join(questions) == x_out.getvalue(), \
		#	'\n[%s] != \n[%s]' % ("".join(questions), x_out.getvalue())
		return config_changed


	def test_command_config_with_invalid_smtp(self):
		config_changed = self.mm_config_fill()
		citems = self.get_default_config_scheme()
		config = SafeConfigParser()
		config.read(self.config_path)
		assert config.has_section('Mail')
		assert config.items('Mail') == citems, \
			"\n[%s]\n[%s]" % (config.items('Mail'), citems)


	def test_command_config_with_valid_smtp(self):
		# START SMTPD
		p1 = Popen(['./tests/smtp_server.py'], stdin=PIPE)
		import time
		time.sleep(0.1)
		config_changed = self.mm_config_fill()
		p1.terminate()
		p1.wait()
		citems = self.get_testserver_config_scheme()
		config = SafeConfigParser()
		config.read(self.config_path)
		assert config.has_section('Mail')
		assert config.items('Mail') == citems, \
			"\n[%s]\n[%s]" % (config.items('Mail'), citems)

	def test_command_send(self):
		# START SMTPD
		tfile = tempfile.NamedTemporaryFile()
		tfile_name = tfile.name
		tfile.close()
		p1 = Popen(['./tests/smtp_server.py', tfile_name], stdin=PIPE)
		citems = self.get_testserver_config_scheme()
		proj_dir = self.mm_create_project('Test')
		config = SafeConfigParser()
		config.read(self.config_path)
		for item in citems:
			config.set('Mail', item[0], item[1])
		files = ['mail.txt', 'subject.txt', 'keys.csv', 'attachments.txt']
		self.create_with_sample_files("", proj_dir, files)
		config.write(open(self.config_path, 'w'))
		sys.stdin = x_in = StringIO('\n')
		sys.stdout = x_out = StringIO()
		m = MMailer()
		m.command_send(args=['mmailer', 'send'])
		sys.stdin = sys.__stdin__
		sys.stdout = sys.__stdout__
		p1.terminate()
		p1.wait()
		of = open('tests/samples/send_output.txt','r')
		sto_str = of.read()
		sto = sto_str.decode('UTF-8')
		# exclude first line from compare,
		# because the date changes each test run
		assert x_out.getvalue() == sto,"\n\n[%s]\n\n[%s]" \
				% (sto, x_out.getvalue())
		import filecmp
		assert filecmp.cmp(tfile_name, 'tests/samples/sended.txt')
