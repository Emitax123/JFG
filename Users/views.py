from django.conf import settings
from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect 

# Create your views here.
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            #redurict to the previus pag
            next_url = request.POST.get('next') or settings.LOGIN_REDIRECT_URL
            return redirect(next_url)
        

           
        else:
            error = True
            return render(request, 'login.html', {'error': error, 'next': request.GET.get('next', '')})
    else:
        return render(request, 'login.html',  {'next': request.GET.get('next', '')})