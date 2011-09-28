#!/usr/bin/env python2

from datetime import datetime
import email
from email.iterators import typed_subpart_iterator
from email.utils import parsedate
import re

from django.core.management import setup_environ
import settings

setup_environ(settings)

from django.utils.html import strip_tags
from django.utils.text import unescape_entities
from tracker.models import User, Exchange
import imaplib2

def scrape(debug=0):
    """
    Connects to GMail account specified by SCRAPER_USER and SCRAPER_PASSWORD.
    Idles until a message from SCRAPER_GOOGLE_GROUP arrives, at which point the
    sender of the message is added into the User model with 0 points if
    necessary. The body of the message is then analyzed to extract possible
    places where shan points might have been given out.
    """
    imap = imaplib2.IMAP4_SSL('imap.gmail.com', debug=debug)
    imap.login(settings.SCRAPER_USER, settings.SCRAPER_PASSWORD)
    imap.select('INBOX')

    try:
        while True: # wheeeeeeeeee!
            typ, data = imap.search(None, 'UNSEEN')

            if typ != 'OK':
                continue

            for num in data[0].split():
                imap.fetch(num, 'RFC822', callback=processEmail, cb_arg=num)

            # block until further activity / timeout
            imap.idle(timeout=600)
    finally:
        imap.logout()

def processEmail((response, num, error)):
    """
    Meant to be used as a callback to the IMAP fetch command. Converts the body
    of the email to email.Message components. Processes each text body before
    html bodies, and calls processMessage() on them after cleaning them with
    cleanText() or cleanHtml().
    """
    if response is None:
        return

    typ, data = response
    if typ != 'OK':
        return

    message = email.message_from_string(data[0][1])
    if message['X-Google-Group-Id'] != settings.SCRAPER_GOOGLE_GROUP:
        print 'Discarding %s' % message['Subject']
        return

    from_header = message['From']
    if from_header is None:
        return
    from_header = from_header.strip()

    match = re.match(r'^(.*?)\s*<(.*)>$', from_header)
    if match is not None:
        # From header of the form: Foo Bar <foobar@example.com>
        from_name = match.group(1)
        from_email = match.group(2)
    else:
        # From header of the form: foobar@example.com
        from_name = ''
        from_email = from_header

    from_user, created = User.objects.get_or_create(
        email=from_email,
        defaults={'name': from_name, 'points': 0}
    )

    ts = datetime(*parsedate(message['Date'])[0:6]) or datetime.now()

    # prefer text versions over HTML versions
    # FIXME: we return as soon as we give out a single shanpoint. The working
    # assumption here is that these different content-types are different
    # versions of the same message, which may or may not be the case. This
    # breaks if for example, I have two text/plain's that give points to a
    # different set of people. Only the people in the first text/plain will be
    # processed.
    for msg in typed_subpart_iterator(message, 'text', 'plain'):
        if processMessage(from_user, ts, cleanText(msg.get_payload())) != 0:
            return

    for msg in typed_subpart_iterator(message, 'text', 'html'):
        if processMessage(from_user, ts, cleanHtml(msg.get_payload())) != 0:
            return

def processMessage(from_user, ts, msg):
    """
    Processes a single message from the User object from_user. Looks for
    patterns like 'foobar +1' or 'foobar ++' and tries to decode the user for
    the name mentioned and give that user points. A name must be at least
    4 characters long.

    Note that a single message can give at most one point to a User.

    Returns the number of points that were successfully given out.
    """
    processed = set()
    for name in re.finditer(r'(\S\S\S+) *\+(1|\+)', msg):
        to_user = decodeUser(name.group(1))
        if to_user is not None and to_user.pk not in processed and \
                to_user.pk != from_user.pk:
            to_user.points += 1
            to_user.save()
            processed.add(to_user.pk)

            # log this
            print '%s gave to %s' % (from_user.email, to_user.email)
            Exchange(from_user=from_user, to_user=to_user, timestamp=ts).save()

    return len(processed)

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

    >>> cleanText('foo\n>bar\n>qux\nspam')
    'foo\n\n\nspam'
    """
    regex = re.compile(r'^>.*$', re.MULTILINE)
    return regex.sub('', text)

def cleanHtml(html):
    """
    Returns a text version of html, by first removing any text in <blockquote>
    tags and then striping any other tags and replacing html entities. The
    <blockquote> strip is done for the same reasons as in cleanText().

    >>> cleanHtml('foo\n<blockquote some-attr="some">bar</blockquote>&amp;st')
    'foo\n&st'
    >>> cleanHtml('foo\n<blockquote\nsome-attr="some">bar</blockquote>&amp;st')
    'foo\n&st'
    """
    regex = re.compile(r'<blockquote.*</blockquote>', re.DOTALL)
    html = regex.sub('', html)
    return unescape_entities(strip_tags(html))

if __name__ == '__main__':
    scrape()
