from django.shortcuts import render_to_response
from tracker.models import User

def list(request):
    return render_to_response(
        'list.html',
        {'users': User.objects.order_by('-points').all()}
    )
