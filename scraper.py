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
    """
    Meant to be used as a callback to the IMAP fetch command. Converts the body
    of the email to email.Message components. Processes each text body before
    html bodies, and calls processMessage() on them after cleaning them with
    cleanText() or cleanHtml().
    """
    typ, data = response
    if typ != 'OK':
        return

    message = email.message_from_string(data[0][1])
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

    # buckets for different Content-Types
    # FIXME: this is ugly as sin
    contents = {'text/plain': [], 'text/html': []}
    def bucketize(msg):
        ct = msg.get_content_type()
        if ct in contents:
            try:
                # closure over contents
                contents[ct].append(msg)
            except KeyError:
                pass

    if not message.is_multipart():
        bucketize(message)
    else:
        # FIXME: I'm assuming there can be at most one level of nesting for
        # multipart messages. If not, I need to rewrite this function in a
        # recursive manner.
        for msg in message.get_payload():
            bucketize(msg)

    # prefer text versions over HTML versions
    # FIXME: we return as soon as we give out a single shanpoint. The working
    # assumption here is that these different content-types are different
    # versions of the same message, which may or may not be the case. This
    # breaks if for example, I have two text/plain's that give points to a
    # different set of people. Only the people in the first text/plain will be
    # processed.
    for t in contents['text/plain']:
        if processMessage(from_user, cleanText(t.get_payload())) != 0:
            return

    for h in contents['text/html']:
        if processMessage(from_user, cleanHtml(h.get_payload())) != 0:
            return

def processMessage(from_user, ts, msg):
    """
    Processes a single message from the User object from_user. Looks for
    patterns like 'foo +1' or 'foo ++' and tries to decode the user from the
    name mentioned and give that user points.

    Note that a single message can give at most one point to a User.

    Returns the number of points that were successfully given out.
    """
    processed = set()
    for name in re.finditer(r'(\S+) *\+(1|\+)', msg):
        to_user = decodeUser(name.group(1))
        if to_user is not None and to_user.pk not in processed and \
                to_user.pk != from_user.pk:
            to_user.points += 1
            to_user.save()
            processed.add(to_user.pk)

            # log this
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
    return re.sub(r'^>.*$', '', text, flags=re.MULTILINE)

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
    html = re.sub(r'<blockquote.*</blockquote>', '', html, flags=re.DOTALL)
    return unescape_entities(strip_tags(html))

if __name__ == '__main__':
    scrape(3)
