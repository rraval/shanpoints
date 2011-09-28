import re
from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter(name='emailaddress')
@stringfilter
def emailaddress(value):
    return re.sub(r'(?<=@.).*$', '', value)

