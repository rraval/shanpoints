from django.db import models

class User(models.Model):
    name = models.CharField(max_length=50, blank=True, db_index=True)
    email = models.EmailField(unique=True)
    points = models.PositiveIntegerField(db_index=True)

    class Meta:
        ordering = ('-points',)

    def __unicode__(self):
        return '%s <%s>' % (self.name, self.email)

class Exchange(models.Model):
    from_user = models.ForeignKey(User, related_name='+')
    to_user = models.ForeignKey(User, related_name='+')
    timestamp = models.DateTimeField()

    def __unicode__(self):
        return '%s to %s on %s' % (self.from_user.name, self.to_user.name, self.timestamp)
