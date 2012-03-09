#!/usr/bin/env python
#-*- coding:utf-8 -*-

import smtpd
import asyncore
import sys

class CustomFileSMTPServer(smtpd.SMTPServer):

	def __init__(*args, **kwargs):
		smtpd.SMTPServer.__init__(*args, **kwargs)


	def set_ofile(self,name):
		self.ofile = open(name, 'w')

	def process_message(self, peer, mailfrom, rcpttos, data):
		out = self.ofile
		out.write('Receiving message from: %s\n' % peer[0])
		out.write('Message addressed from: %s\n' % mailfrom)
		out.write('Message addressed to  : %s\n' % rcpttos)
		out.write('Message length        : %s\n' % len(data))
		out.close()
		return


def main():
	if len(sys.argv) == 2:
		ofile = sys.argv[1]
	else:
		ofile = '/dev/null'
	server = CustomFileSMTPServer(('127.0.0.1', 1555), None)
	server.set_ofile(ofile)
	asyncore.loop()

if __name__ == '__main__':
	sys.exit(main())
