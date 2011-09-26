#!/usr/bin/env python2
import imaplib2, psycopg2, email

class ShanPoints(object):
    def __init__(self, imap):
        self.imap = imap

    def fetch(self, (response, num, error)):
        typ, data = response
        message = email.message_from_string(data[0][1])
        print 'Message %s: %s' % (num, message['Subject'])
        for m in message.get_payload():
            print m.get_payload()
        print '%s' % message
        print '---'

imap = imaplib2.IMAP4_SSL('imap.gmail.com')#, debug=4)
imap.login('shanpoints@gmail.com', 'shanisawesome')
imap.select('INBOX')

shan = ShanPoints(imap)

#imap.idle()
typ, data = imap.search(None, 'ALL')
for num in data[0].split():
    imap.fetch(num, 'RFC822', callback=shan.fetch, cb_arg=num)

imap.logout()
