from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect 
from django.contrib.auth.views import LoginView
from .forms import CustomLoginForm

# Create your views here.

class CustomLoginView(LoginView):
    template_name = 'templates/login.html'
    authentication_form = CustomLoginForm
    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', '/')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            #redurict to the previus pagE
            return redirect(request.META.get('HTTP_REFERER', '/'))
           
        else:
            error = True
            return render(request, 'login.html', {'error': error})
    else:
        return render(request, 'login.html')