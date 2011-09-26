#!/usr/bin/env python2

import email
import re

from django.core.management import setup_environ
import settings

setup_environ(settings)

from django.utils.html import strip_tags
from django.utils.text import unescape_entities
from tracker.models import User
import imaplib2

def scrape(debug=0):
    """
    Connects to GMail account specified by SCRAPER_USER and SCRAPER_PASSWORD.
    Idles until a message from SCRAPER_MAILING_LIST arrives, at which point the
    sender of the message is added into the User model with 0 points if
    necessary. The body of the message is then analyzed to extract possible
    places where shan points might have been given out.
    """
    imap = imaplib2.IMAP4_SSL('imap.gmail.com', debug=debug)
    imap.login(settings.SCRAPER_USER, settings.SCRAPER_PASSWORD)
    imap.select('INBOX')

    try:
        while True: # wheeeeeeeeee!
            typ, data = imap.search(None, 'UnSeen')
            for num in data[0].split():
                imap.fetch(num, 'RFC822', callback=processEmail, cb_arg=num)

            # block until further activity / timeout
            imap.idle()
    finally:
        imap.logout()

def processEmail((response, num, error)):
    typ, data = response
    if typ != 'OK':
        return

    message = email.message_from_string(data[0][1])
    print '%s' % message

def decodeUser(name):
    """
    Map a name to a possible User object. The following heuristics are applied,
    with respective priority and the process is ended as soon as a single match
    is found.

        - name is a case insensitive substring of only one user's email
        - name is a case insensitive substring of only one user's name

    If no User object can be located, None is returned.
    """
    # let's flex our Haskell muscles and do something lazy
    patterns = (
        lambda: User.objects.filter(email__contains=name)[:2],
        lambda: User.objects.filter(name__contains=name)[:2]
    )

    for pat in patterns:
        res = pat()
        if len(res) == 1:
            return res[0]

    return None

def cleanText(text):
    """
    Returns a version of text with all lines starting with '>' removed. This is
    to prevent quoted text from previous emails being interpreted as an exchange
    of shan points.
    """
    return re.sub(r'^>.*$', '', text, flags=re.MULTILINE)

def cleanHtml(html):
    """
    Returns a text version of html, by first removing any text in <blockquote>
    tags and then striping any other tags and replacing html entities. The
    <blockquote> strip is done for the same reasons as in cleanText().
    """
    html = re.sub(r'<blockquote.*</blockquote>', '', html, flags=re.DOTALL)
    return unescape_entities(strip_tags(html))

if __name__ == '__main__':
    scrape(3)
