#!/usr/bin/env python2

from django.core.management import setup_environ
import settings

setup_environ(settings)

from tracker.models import User
import imaplib2

def decodeUser(name):
    """
    Map a name to a possible User object. The following heuristics are applied,
    with respective priority and the process is ended as soon as a single match
    is found.

        - name is a case insensitive substring of only one user's email
        - name is a case insensitive substring of only one user's name

    If no User object can be located, None is returned.
    """
    patterns = (
        lambda: User.objects.filter(email__contains=name)[:2],
        lambda: User.objects.filter(name__contains=name)[:2]
    )

    for pat in patterns:
        res = pat()
        if len(res) == 1:
            return res[0]

    return None

def scrape():
    """
    Connects to GMail account specified by SCRAPER_USER and SCRAPER_PASSWORD.
    Idles until a message from SCRAPER_MAILING_LIST arrives, at which point the
    sender of the message is added into the User model with 0 points if
    necessary. The body of the message is then analyzed to extract possible
    places where shan points might have been given out.
    """
    pass

if __name__ == '__main__':
    scrape()