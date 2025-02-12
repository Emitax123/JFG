from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator, PageNotAnInteger
from .forms import ProjectForm, FileFieldForm, DecimalForm
from .models import Project, Client, Event, ProjectFiles
from django.db.models import Q
from decimal import Decimal as Dec
from datetime import datetime
from .functions import month_str
from collections import defaultdict
# Create your views here.

#Vista principal
def index(request):
    projects = Project.objects.all()
    return render (request, 'index.html', {'projects':projects})

# charts/views.py

def chart_data(request):
    if request.method == 'POST':
        date = request.POST.get('date')
        date_split = date.split("-")
        month = int(date_split[1])
        year = int(date_split[0])
    else:
        month = datetime.now().month
        year = datetime.now().year
    projects = Project.objects.filter(created__month=month, created__year=year).exclude(price=None, adv=None, gasto=None)
    total = sum(item.price for item in projects)
    gastos = sum(item.gasto for item in projects)
    cobro = sum(item.adv for item in projects)
    labels = ['Total', 'Gastos', 'Cobro']
    values = [total, gastos, cobro]
    backg = ['red', 'blue', 'green']
    chart_data = {
        'label': 'Balance',
        'labels': labels,
        'values': values,
        'chart_type': 'doughnut',
        'barckgroundColor':backg,
    }
    
    return JsonResponse(chart_data)

#Calculo de los meses a mostrar
def generate_month_data(months, year):
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    for y in range(2023, current_year + 1):
        year.append({'year':y})
        end_month = 12 if y < current_year else current_month
        for m in range(1, end_month + 1):
            months.append({'year': y, 'month': m})

    return months, year

#Vista del balance
def balance(request):
    if request.method == 'POST':
        date = request.POST.get('date')
        date_split = date.split("-")
        month = int(date_split[1])
        year = int(date_split[0])
    else:
        month = datetime.now().month
        year = datetime.now().year
    projects = Project.objects.filter(created__month=month, created__year=year).exclude(price=None, adv=None, gasto=None)
    if not projects:
        non_exist = True
        return render (request, 'balance_template.html', {'non_exist':non_exist})
    cant = projects.count()
    total = sum(item.price for item in projects)
    adv = sum(item.adv for item in projects)
    gastos = sum(item.gasto for item in projects)
    if total > 0:
        percent = round((adv/total)*100 , 2)
    else:
        percent = 0
    net = adv-gastos
    return render (request, 'balance_template.html', {'total':total, 'adv':adv, 'cant':cant, 'percent':percent, 'gastos':gastos, 'net':net, 'month':month_str(month), 'year':year})

#Vista de los proyectos
def projectlist_view(request):
    if request.method == 'POST':
        if request.POST.get('search-input')!="":
            query = request.POST.get('search-input')
            projects = Project.objects.filter(
                 Q(client__name__icontains=query) | Q(partido__icontains=query)
            ).order_by('-created')
            
            if not projects:
            
                return render (request, 'project_list_template.html', {'no_projects':True})    
        return render (request, 'project_list_template.html', {'projects':projects})
    else:
        num_page = request.GET.get('page')
        pages = Paginator (Project.objects.all().order_by('created'), 8)
        try:
            actual_pag = pages.get_page(num_page)
        except PageNotAnInteger:
            actual_pag = pages.get_page(1)
    return render (request, 'project_list_template.html', {'projects':actual_pag, 'pages':pages})


def project_view(request,pk):
    project = Project.objects.get(pk=pk)
    form = FileFieldForm()
    return render(request, 'project_template.html', {'project':project, 'form':form})

#Registro en historial
def save_in_history(pk, type, msg):
    event = Event.objects.create(model_pk=pk, type=type, msg=msg)

#Vista formulario de creacion
def create_view(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)    
        if form.is_valid():
            form_instance = form.save(commit=False)
            if request.POST.get('client-list')!="":
                client_pk = request.POST.get('client-list')
                form_instance.client = Client.objects.get(pk=client_pk)
            else:
                client_instance = Client()
                client_instance.name = request.POST.get('client-name')
                client_instance.dni = request.POST.get('client-dni')
                client_instance.phone = request.POST.get('client-phone')
                form_instance.client = client_instance
                client_instance.save()
            #Si el cliente es el titular
            if request.POST.get('client-titular-checkbox') == 'on':
                #Asignamos los datos de clienta al titular
                form_instance.titular_name = form_instance.client.name
                form_instance.titular_dni = form_instance.client.dni
                form_instance.titular_phone = form_instance.client.phone
               
            form_instance.save()#Se guarda la instancia 
            msg = "Se ha creado un nuevo proyecto"   
            pk = form_instance.pk
            save_in_history(pk, 2, msg)

            if 'save_and_backhome' in request.POST:
                    return redirect('projects')
        else:
            # Form data is not valid, handle the errors
            errors = form.errors.as_data()
            for field, error_list in errors.items():
                for error in error_list:
                    # Access the error message for each field
                    error_message = error.message
                    print(f"Error for field '{field}': {error_message}")    
    form = ProjectForm()
    clients = Client.objects.all()
    return render (request, 'form.html', {'form':form, 'clients':clients})

#vista de moficicacion
def mod_view(request, pk):
    if request.method == 'POST':
        instance = Project.objects.get(pk=pk)
        if request.POST.get('proc'):
            instance.procedure = request.POST.get('proc')
        if request.POST.get('insctype'):
            instance.inscription_type = request.POST.get('insctype')
        if request.POST.get('price'):
            if isinstance(request.POST.get('price'), int):
                print(request.POST.get('price'))
            instance.price = request.POST.get('price')
        if request.POST.get('adv'):
            instance.adv = instance.adv + Dec(request.POST.get('adv'))
        if request.POST.get('gasto'):
            instance.gasto = instance.gasto + Dec(request.POST.get('gasto'))
        
        instance.save()
        msg = "Se ha modificado un proyecto"   
        pk = instance.pk
        save_in_history(pk, 1, msg)

    prev = request.META.get('HTTP_REFERER')
    return redirect(prev)


#Vista de historial
def history_view(request):
    history = Event.objects.order_by('-time')
    grouped_objects_def = defaultdict(lambda: defaultdict(list))
    for h in history:
        year = h.time.year
        print(year)
        month = h.time.month
        grouped_objects_def[year][month].append(h)
    for obj in grouped_objects_def:            
       grouped_objects_def[obj].default_factory = None
    grouped_objects = dict(grouped_objects_def)
    return render (request, 'history_template.html', {'yearlist':grouped_objects})

def search(request):
    
    query = request.GET.get('query')  # Get the search query from the request
    # Perform your search logic here and get the results
    if query:
        objectcs = Project.objects.filter(
                 Q(client__name__icontains=query) | Q(partido__icontains=query)
            ).order_by('-created')[:5]
        results = []
        for obj in objectcs:
            obj_dict = obj.__dict__
            obj_dict['datecreated'] = obj.created.strftime('%d/%m/%Y')
            del obj_dict['_state']
            results.append(obj_dict)
    else:
        results = list(Project.objects.none())
    
    return JsonResponse({'results': results}, safe=False)

def upload_files(request, pk):
    if request.method == 'POST':
        form = FileFieldForm(request.POST, request.FILES)
        if form.is_valid():
          
          files = form.cleaned_data['file_field']
          for f in files:
              print(f.name)
              file_instance = ProjectFiles(project = Project.objects.get(pk=pk), files = f)
              file_instance.save()  

    prev = request.META.get('HTTP_REFERER')
    return redirect(prev)

def file_view(request, pk):
    files = ProjectFiles.objects.filter(project__pk = pk)
    print(files)
    return render (request, 'files_template.html', {'files':files})   

