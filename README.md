Shan Points
===========

Shan points are karma in a way, except you only get one point at a time and
can't get negative feedback (i.e. your shan points are monotonically increasing
over time). This project is an google groups / email tracker of the exchange of
Shan points.

Functional Overview
-------------------

Whenever a google group forwards a message to a specific GMail account, the
sender is added to the database with 0 initial Shan points. Every email may
contain patterns of the form ``name +1`` or ``name ++``, with no limit on
the number of names. Note that a name must be at least 3 characters and that
prefix forms work as well (``+1 name`` and ``++ name``).

Names are resolved to specific users, and if successful, their Shan points are
incremented. See ``decodeUser`` in ``scraper.py`` for resolution rules. Note
that a user may receive at most one Shan point per email. Trying to give a user
more than one point or give yourself a point will fail miserably.

Usage
-----

All the code is built on top of the Django framework. Why? Because Django has a
fantastic ORM and I like Python. To get things rolling, enable the ``tracker``
app in ``settings.py`` and run the standard ``manage.py syncdb``.

Now create a GMail account and subscribe it to the Google Group you'd like to
track. Put the account details in ``SCRAPER_USER`` and ``SCRAPER_PASSWORD`` in
``settings.py``. Figure out the google group id for your group (which is
specified in the ``X-Google-Group-Id`` header in every email from the group) in
``SCRAPER_GOOGLE_GROUP`` as well.

Finally, run ``scraper.py``. This will sign into the GMail account, block until
there's a new email, and will update the database with Shan point values if
necessary.

TODO
====

Lots of stuff. grep for ``FIXME`` in the codebase.
