from django.db import models

class User(models.Model):
    name = models.CharField(max_length=50, blank=True, db_index=True)
    email = models.EmailField(unique=True)
    points = models.PositiveIntegerField()

    def __unicode__(self):
        return '%s <%s>' % (self.name, self.email)
