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
            return redirect('projects')
        else:
            return render(request, 'login.html', {'error': 'Contraseña o usuario incorrecto'})
    else:
        return render(request, 'login.html')