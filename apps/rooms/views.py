from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def room_list(request):
    return render(request, 'rooms/room_list.html')
