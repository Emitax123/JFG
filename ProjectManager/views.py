
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator, PageNotAnInteger
from .forms import ProjectForm, FileFieldForm, ProjectFullForm
from .models import Project, Client, Event, ProjectFiles
from django.db.models import Q
from decimal import Decimal as Dec
from datetime import datetime
import time
from .functions import month_str
from collections import defaultdict
from .supabase_client import supabase
import os
import logging
logger = logging.getLogger(__name__)
from django.http import FileResponse

import io
from urllib.request import urlopen
from urllib.error import URLError



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
#add a delete project function
def delete_view(request, pk):
    project = Project.objects.get(pk=pk)
    event = Event.objects.filter(model_pk=pk).first()
    if request.method == 'POST':
        msg = "Se ha eliminado un proyecto"
        project.delete()
        event.delete()
        file = ProjectFiles.objects.filter(project_pk=pk).first()
        if file :
            delete_file(request, pk)
        save_in_history(pk, 3, msg)
        return redirect('projects')
    return redirect('index')

def balance_anual(request,monthly_data, monthly_totals, year):
    year = datetime.now().year
    projects = Project.objects.filter(created__year=year).exclude(price=None, adv=None, gasto=None)
    if not projects:
        non_exist = True
        return render (request, 'balance_template.html', {'non_exist':non_exist})
    # Create a list to store monthly data
   

    # Divide projects into months
    for project in projects:
        month = project.created.month - 1  # Subtract 1 since list indices start at 0
        monthly_data[month].append(project)

    # Calculate totals for each month
  
    for month_index, month_projects in enumerate(monthly_data):
        if not month_projects:
            monthly_totals.append({'total': 0, 'gastos': 0, 'cobro': 0, 'neto': 0, 'cant': 0, 'month_name': month_str(month_index + 1)})
            continue
            
        month_name = month_str(month_projects[0].created.month)
        cant = len(month_projects)
        total = sum(p.price for p in month_projects)
        gastos = sum(p.gasto for p in month_projects)
        cobro = sum(p.adv for p in month_projects)
        neto = cobro - gastos
        monthly_totals.append({'total': total, 'gastos': gastos, 'cobro': cobro , 'neto': neto, 'cant': cant, 'month_name': month_name})
    for month in monthly_totals:
        print(month.get('total'))
    
    return (request,
        monthly_data,
        monthly_totals, 
        year)


#Vista del balance
def balance(request):
    if request.method == 'POST':
        #Aqui el user selecciona el mes y año
        date = request.POST.get('date')
        date_split = date.split("-")
        month = int(date_split[1])
        year = int(date_split[0])
    else:
        #Si no selecciona nada, se toma el mes y año actual
        month = datetime.now().month
        year = datetime.now().year
    
    projects = Project.objects.filter(created__month=month, created__year=year).exclude(price=None, adv=None, gasto=None)
    if not projects:
        non_exist = True
        return render (request, 'balance_template.html', {'non_exist':non_exist})
    #Cant = cantidad de proyectos
    cant = projects.count()
    #Total = suma de los presupuestos
    total = sum(item.price for item in projects)
    #adv = suma de los anticipos
    adv = sum(item.adv for item in projects)
    #gastos = suma de los gastos
    gastos = sum(item.gasto for item in projects)
    if total > 0:
        percent = round((adv/total)*100 , 2)
    else:
        percent = 0
    #net = el neto, es decir los anticipos menos los gastos
    net = adv-gastos
    #Formateamos los numeros a 2 decimales y cambiamos el punto por la coma
    adv = f"{adv:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    total = f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    gastos = f"{gastos:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    net = f"{net:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    #Creamos la lista anual y la lista que sume los totales de cada mes
    monthly_data = [[] for _ in range(12)]
    monthly_totals = []
    
    balance_anual(request, monthly_data, monthly_totals, datetime.now().year)

    return render (request, 'balance_template.html', {
        'total':total, 
        'adv':adv, 
        'cant':cant, 
        'percent':percent, 
        'gastos':gastos, 
        'net':net, 
        'month':month_str(month), 
        'year':year,
        'monsths_list': monthly_data,
        'monthly_totals': monthly_totals,
        
        })

#Vista de los proyectos todos
def projectlist_view(request):
    print("paginas")
    if request.method == 'POST':
        print("metodo post")
        if request.POST.get('search-input')!="":
            query = request.POST.get('search-input')
            projects = Project.objects.filter(
                 Q(client__name__icontains=query) | Q(partido__icontains=query)
            ).order_by('-created')
            num_page = request.GET.get('page')
            pages = Paginator (projects, 10)
            try:
               actual_pag = pages.get_page(num_page)
            except PageNotAnInteger:
               actual_pag = pages.get_page(1)
            if not projects:
                return render (request, 'project_list_template.html', {'no_projects':True})
    
        return render (request, 'project_list_template.html', {'projects':actual_pag, 'pages':pages})
    else:
        num_page = request.GET.get('page')
        pages = Paginator (Project.objects.all().order_by('-created'), 10)
        try:
            actual_pag = pages.get_page(num_page)
        except PageNotAnInteger:
            actual_pag = pages.get_page(1)
        print(pages.num_pages)
    return render (request, 'project_list_template.html', {'projects':actual_pag, 'pages':pages})

#Lista de proyectos por cliente
def alt_projectlist_view(request, pk):
    projects = Project.objects.filter(client__pk__icontains=pk).order_by('-created')
    num_page = request.GET.get('page')
    pages = Paginator (projects, 10)
    try:
        actual_pag = pages.get_page(num_page)
    except PageNotAnInteger:
        actual_pag = pages.get_page(1)
    if not projects:
        return render (request, 'project_list_template.html', {'no_projects':True})   
    return render (request, 'project_list_template.html', {'projects':actual_pag, 'pages':pages})

def project_view(request,pk):
    project = Project.objects.get(pk=pk)
    file = ProjectFiles.objects.filter(project_pk=pk).first()
    if file:
        file_url = file.url
        return render(request, 'project_template.html', {'project':project, 'file_url':file_url})
    else:
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
            if request.POST.get('client-pk'):
                client_pk = request.POST.get('client-pk')
                form_instance.client = Client.objects.get(pk=client_pk)
            if request.POST.get('client-list')!="":
                client_pk = request.POST.get('client-list')
                form_instance.client = Client.objects.get(pk=client_pk)
            else:
                # First try to find an existing client with the same name
                existing_client = Client.objects.filter(name=request.POST.get('client-name')).first()
                if existing_client:
                    form_instance.client = existing_client
                else:
                    # If no existing client found, create new one
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
        if request.POST.get('contact_name'):
            instance.contact_name = request.POST.get('contact_name')
            instance.contact_phone = request.POST.get('contact_phone')        
        if request.POST.get('client-data') == '':
            instance.titular_name = instance.client.name
            instance.titular_phone = instance.client.phone
        if request.POST.get('titular'):
            instance.titular_name = request.POST.get('titular')
        if request.POST.get('titular_phone'):
            instance.titular_phone = request.POST.get('titular_phone')
        if request.POST.get('proc'):
            instance.procedure = request.POST.get('proc')
        if request.POST.get('insctype'):
            instance.inscription_type = request.POST.get('insctype')
        if request.POST.get('price'):
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

#Modificacion total del proyecto
def full_mod_view(request, pk):
    if request.method == 'POST':
        instance = Project.objects.get(pk=pk)
        form = ProjectFullForm(request.POST, instance=instance) 
        if form.is_valid():
            print("El formulario es valido")
            form.save()
            msg = "Se ha modificado un proyecto"   
            pk = instance.pk
            save_in_history(pk, 1, msg)
            return redirect('projectview', pk=pk)
    else:
        instance = Project.objects.get(pk=pk)
        form = ProjectFullForm(instance=instance)
    return render (request, 'full_mod_template.html', {'form':form, 'project':instance})

#Vista de historial
def history_view(request):
    history = Event.objects.order_by('-time')
    grouped_objects_def = defaultdict(lambda: defaultdict(list))
    for h in history:
        year = h.time.year
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
                 Q(client__name__icontains=query) | Q(partida__icontains=query)
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



def download_file(request, pk):
    file = ProjectFiles.objects.get(project_pk=pk)
    file_name = file.name
    bucket_name = os.getenv('SUPABASE_BUCKET')
    file_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
    try:
        response = urlopen(file_url)
        file_content = io.BytesIO(response.read())
        return FileResponse(file_content, as_attachment=True, filename=file_name)
    except URLError as e:
        logger.error(f"Error downloading file: {str(e)}")
        return JsonResponse({'error': 'Failed to download file'}, status=500)

def upload_files(request, pk):
    if request.method == 'POST':
        form = FileFieldForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file_field']
            file_content = file.read()
            timestamp = int(time.time())
            file_name = f"{pk}_{timestamp}_{file.name}"
            bucket_name = os.getenv('SUPABASE_BUCKET')
            supabase.storage.from_(bucket_name).upload(file_name, file_content)
            file_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
            ProjectFiles.objects.create(project_pk=pk, name=file_name, url=file_url)

    prev = request.META.get('HTTP_REFERER')
    return redirect(prev)

def delete_file(request, pk):
    file = ProjectFiles.objects.get(project_pk=pk)
    bucket_name = os.getenv('SUPABASE_BUCKET')
    supabase.storage.from_(bucket_name).remove([file.name])
    file.delete()
    prev = request.META.get('HTTP_REFERER')
    return redirect(prev)

def file_view(request, pk):
    files = ProjectFiles.objects.filter(project_pk = pk)
    
    return render (request, 'files_template.html', {'files':files})   

def create_client_view(request):
    if request.method == 'POST':
        if request.POST.get('name') != '':
            client = Client.objects.create(name=request.POST.get('name'), phone=request.POST.get('phone'), flag = True)
            client.save() 
            return redirect('clients')
    return render (request, 'create_client_template.html')

def clients_view(request):
    if request.method == 'POST':
        if request.POST.get('client-name') != '':
            client = Client.objects.create(name=request.POST.get('client-name'), dni=request.POST.get('client-dni'), phone=request.POST.get('client-phone'))
            client.save()
            return redirect('clients')
    clients = Client.objects.filter(flag=True).order_by('name')
    return render (request, 'clients_template.html', {'clients':clients})

def create_for_client(request, pk):
    if request.method == 'POST':
        form = ProjectForm(request.POST)    
        if form.is_valid():
            form_instance = form.save(commit=False)
            form_instance.client = Client.objects.get(pk=pk)
            form_instance.save()#Se guarda la instancia 
            msg = "Se ha creado un nuevo proyecto"   
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
    return render (request, 'project_for_client.html', {'form':form})
