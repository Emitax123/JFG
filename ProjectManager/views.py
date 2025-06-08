from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator, PageNotAnInteger

from Accounting.models import Account
from .forms import ProjectForm, FileFieldForm, ProjectFullForm
from .models import Project, Client, Event, ProjectFiles
from django.db.models import Q, Sum, Count, ExpressionWrapper, F, FloatField
from django.db.models.functions import ExtractMonth
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
from django.contrib.auth.decorators import login_required
import io
from urllib.request import urlopen
from urllib.error import URLError
from django.db import DatabaseError, transaction
from Accounting.views import create_acc_entry, create_account

#Manejo de paginacion
def paginate_queryset(request, queryset, per_page=12):
    """Paginate any queryset and handle pagination errors"""
    num_page = request.GET.get('page')
    paginator = Paginator(queryset, per_page)
    try:
        page_obj = paginator.get_page(num_page)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    return page_obj, paginator

#Vista principal
def index(request):
    return render (request, 'Index.html')

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
        
    accounts = Account.objects.filter(
        project__created__month=month, 
        project__created__year=year
    ).select_related('project')

    sums = accounts.aggregate(
        total_estimated=Sum('estimated'),
        total_advance=Sum('advance'),
        total_expenses=Sum('expenses')
    )
    
    total_estimated = sums['total_estimated'] or 0
    print(total_estimated)
    total_advance = sums['total_advance'] or 0
    total_expenses = sums['total_expenses'] or 0
    labels = ['Total', 'Gastos', 'Cobro']
    values = [total_estimated, total_advance, total_expenses]
    backg = ['red', 'blue', 'green']

   

    # Annotate each project with its net price

    # Aggregate net price by type
    net_by_type = (
        accounts
        .values('project__type')
        .annotate(net_sum=Sum('netWorth'))
        .order_by('project__type')
    )

    # Ensure all variables are always defined, even if not present in net_by_type
    net_estado_parcelario = 0
    net_mensura = 0
    net_amojonamiento = 0
    net_relevamiento = 0
    net_legajo_parcelario = 0

    for entry in net_by_type:
        project_type = entry['project__type']
        if project_type == 'Estado Parcelario':
            net_estado_parcelario = entry['net_sum'] or 0
        elif project_type == 'Mensura':
            net_mensura = entry['net_sum'] or 0
        elif project_type == 'Amojonamiento':
            net_amojonamiento = entry['net_sum'] or 0
        elif project_type == 'Relevamiento':
            net_relevamiento = entry['net_sum'] or 0
        elif project_type == 'Legajo Parcelario':
            net_legajo_parcelario = entry['net_sum'] or 0
    
    labels2 = ['Est.Parcelario', 'Amojonamiento', 'Relevamiento', 'Mensura', 'Legajo Parcelario']
    values2 = [net_estado_parcelario, net_amojonamiento, net_relevamiento, net_mensura, net_legajo_parcelario]
    backg2 = ['red', 'blue', 'green', 'orange', 'purple']

    chart_data = {
        'label1': 'Balance',
        'label2': 'Ganancias por tipo',
        
        'labels2': labels2,
        'values2': values2,
        'labels1': labels,
        'values1': values,
        'chart_type': 'doughnut',
        'barckgroundColor':backg,
        'barckgroundColor2':backg2,
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

    if request.method == 'POST':
        msg = "Se ha eliminado un proyecto " + project.type + " de " + project.client.name
        
        Event.objects.filter(model_pk=pk).delete()
        file = ProjectFiles.objects.filter(project_pk=pk).first()
        if file :
            delete_file(request, pk)
        project.delete()
        save_in_history(pk, 3, msg)
    return redirect('index')

#Archivado de proyectos
def close_view(request, pk):
    project = Project.objects.get(pk=pk)
    project.closed = True
    project.save()
    msg = "Se ha cerrado un proyecto"
    type = 1 #Modificacion
    model_pk = pk
    save_in_history(pk, 1, msg)
    return redirect('projects')

#Formateo de datos
def format_currency(value):
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

#Funcion usada dentro de balance, para mostrar el balance anual
def balance_anual(year):
    # Annotate each project with its month
    monthly = (
        Project.objects
        .filter(created__year=year)
        .exclude(price=None, adv=None, gasto=None)
        .annotate(month=ExtractMonth('created'))
        .values('month')
        .annotate(
            total=Sum('price'),
            gastos=Sum('gasto'),
            cobro=Sum('adv'),
            cant=Count('id')
        )
        .order_by('month')
    )

    # Prepare a list for all 12 months
    monthly_totals = []
    monthly_data = [[] for _ in range(12)]  # If you still want to keep this for compatibility

    # Fill in the months with data or zeros
    monthly_dict = {item['month']: item for item in monthly}
    for m in range(1, 13):
        data = monthly_dict.get(m)
        if data:
            neto = data['cobro'] - data['gastos']
            monthly_totals.append({
                'total': data['total'] or 0,
                'gastos': data['gastos'] or 0,
                'cobro': data['cobro'] or 0,
                'neto': neto,
                'cant': data['cant'],
                'month_name': month_str(m)
            })
        else:
            monthly_totals.append({
                'total': 0,
                'gastos': 0,
                'cobro': 0,
                'neto': 0,
                'cant': 0,
                'month_name': month_str(m)
            })

    neto_anual = sum(d['neto'] for d in monthly_totals)
    neto_anual = format_currency(neto_anual)

    # Format currency for each month's neto
    for month in monthly_totals:
        month['neto'] = format_currency(month['neto'])

    return {
        'monthly_data': monthly_data,
        'monthly_totals': monthly_totals,
        'year': year,
        'neto_anual': neto_anual,
    }

#Balance
@login_required
def balance(request):
    if request.method == 'POST':
        #Aqui el user selecciona el mes y año
        date = request.POST.get('date')
        date_split = date.split("-")
        month = int(date_split[1])
        year = int(date_split[0])
        #Obtengo los proyectos del mes y año seleccionado
        
        projects = Project.objects.filter(created__month=month, created__year=year).exclude(price=None, adv=None, gasto=None)
       

    else:
        #Si no selecciona nada, se toma el mes y año actual
        month = datetime.now().month
        year = datetime.now().year
        #Obtengo los proyectos del mes y año actual, pero solo los que no estan cerrados
        projects = Project.objects.filter(created__month=month, created__year__gte=year-1).exclude(price=None, adv=None, gasto=None, closed=True)
    project_ids = projects.values_list('id', flat=True)
    accounts = Account.objects.filter(project__id__in=project_ids)
    sums_acc = accounts.aggregate(
        adv=Sum('advance'),
        exp=Sum('expenses'),
        net=Sum('netWorth'),
    )
    sums = projects.aggregate(
        total=Sum('price'),
        
    )
    totalEstimatedAmount = sums['total'] or 0
    adv = sums_acc['adv'] or 0
    exp = sums_acc['exp'] or 0
    pending = totalEstimatedAmount - adv - exp
    cant = projects.count()
    cant_actual_month = projects.filter(created__month=month).count()
    cant_previus_months = projects.filter(closed=False).exclude(created__month=month).count()

    if totalEstimatedAmount > 0:
        percent = round(adv/(totalEstimatedAmount-exp)*100 , 2)#adv/totalestimated-exp ARRREGLARRRRR
    else:
        percent = 0
    #net = el neto, es decir los anticipos menos los gastos
    net = adv-exp
    #Formateamos los numeros a 2 decimales y cambiamos el punto por la coma
    adv = format_currency(adv)
    totalEstimatedAmount = format_currency(totalEstimatedAmount)
    exp = format_currency(exp)
    net = format_currency(net)
    pending = format_currency(pending)
    
    #Creamos la lista anual y la lista que sume los totales de cada mes
    data = balance_anual(year)
    non_exist = False
    if not projects.exists():
        non_exist = True
    
    return render (request, 'balance_template.html', {
        'non_exist':non_exist,
        'total':totalEstimatedAmount, 
        'adv':adv, 
        'pending':pending,
        'cant':cant,
        'cant_actual_month':cant_actual_month,
        'cant_previus_months':cant_previus_months,
        'percent':percent, 
        'gastos':exp, 
        'net':net, 
        'month':month_str(month), 
        'year':year,
        'monthly_totals': data['monthly_totals'],
        'monthly_list': data['monthly_data'],
        'neto_anual': data['neto_anual'],
        })

#Todos los proyectos
def projectlist_view(request):
    if request.method == 'POST':
        if request.POST.get('search-input')!="":
            query = request.POST.get('search-input')
            projects = Project.objects.select_related('client').filter(
                 Q(client__name__icontains=query) | Q(partido__icontains=query)
            ).order_by('-created')
            
            if not projects.exists():
                return render (request, 'project_list_template.html', {'no_projects':True})
        actual_pag, pages = paginate_queryset(request, projects)
        return render (request, 'project_list_template.html', {'projects':actual_pag, 'pages':pages})
        
    else:
        actual_pag, pages = paginate_queryset(request, Project.objects.filter(closed=False).order_by('-created'))
    return render (request, 'project_list_template.html', {'projects':actual_pag, 'pages':pages})

#Proyectos por cliente
def alt_projectlist_view(request, pk):
    projects = Project.objects.select_related('client').filter(client__pk=pk).order_by('-created')
    if not projects.exists():
        return render (request, 'project_list_template.html', {'no_projects':True})
    actual_pag, pages = paginate_queryset(request, projects)
    return render (request, 'project_list_template.html', {'projects':actual_pag, 'pages':pages})

#Proyectos por tipo
def projectlistfortype_view(request, type):
    #Mensuras
    type_map = {
        1: "Mensura",
        2: "Estado Parcelario",
        3: "Amojonamiento"
    }
    project_type = type_map.get(type)
    if not project_type:
        return render(request, 'project_list_template.html', {'no_projects': True})
    projects = Project.objects.select_related('client').filter(type=project_type, closed=False).order_by('-created')
    actual_pag, pages = paginate_queryset(request, projects)
    if not projects.exists():
        return render (request, 'project_list_template.html', {'no_projects':True})
    return render (request, 'project_list_template.html', {'projects':actual_pag, 'pages':pages})

#Vista de un proyecto
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
            with transaction.atomic():
                form_instance = form.save(commit=False)
                client = None
                client_pk = request.POST.get('client-pk') or request.POST.get('client-list')
                if client_pk:
                    client = Client.objects.get(pk=client_pk)
                else:
                    client_name = request.POST.get('client-name')
                    client = Client.objects.filter(name=client_name).first()
                    if not client:
                        client = Client.objects.create(
                            name=client_name,
                            phone=request.POST.get('client-phone')
                        )
                form_instance.client = client
                form_instance.save()#Se guarda la instancia
                #Si el cliente es el titular
                msg = "Se ha creado un nuevo proyecto"   
                pk = form_instance.pk
                save_in_history(pk, 2, msg)
                create_account(pk)
                if 'save_and_backhome' in request.POST:
                    return redirect('projectview', pk=pk)
                
        else:
            # Form data is not valid, handle the errors
            errors = form.errors.as_data()
            for field, error_list in errors.items():
                for error in error_list:
                    # Access the error message for each field
                    error_message = error.message
                    print(f"Error for field '{field}': {error_message}")    
    form = ProjectForm()
    clients = Client.objects.all().filter(flag=True, not_listed=False).order_by('name')
    return render (request, 'form.html', {'form':form, 'clients':clients})

#vista de moficicacion
def mod_view(request, pk):
    if request.method == 'POST':
        instance = Project.objects.get(pk=pk)
        msg = "" 
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
            try:
                previous_price = instance.price
                instance.price = Dec(request.POST.get('price'))
                msg = "Se establecio el presupuesto del proyecto " + str(instance.pk)
                create_acc_entry(instance.pk, 'est', previous_price, Dec(request.POST.get('price')))
            except:
                instance.price = Dec("0,00")
        if request.POST.get('adv'):
            try:
                previous_adv = instance.adv
                instance.adv = instance.adv + Dec(request.POST.get('adv'))
                msg = "Se cobraron $" + request.POST.get('adv') + " del proyecto " + str(instance.pk)
                create_acc_entry(instance.pk, 'adv', previous_adv, Dec(request.POST.get('adv')))
            except:
                instance.adv = Dec("0.00")
        if request.POST.get('gasto'):
            try:
                previous_gasto = instance.gasto or Dec("0.00")
                instance.gasto = instance.gasto + Dec(request.POST.get('gasto'))
                msg = "Se debitaron $" + request.POST.get('gasto') + " al proyecto " + str(instance.pk)
                create_acc_entry(instance.pk, 'exp', previous_gasto, Dec(request.POST.get('gasto')))
            except:
                instance.gasto = Dec("0.00")
        if not Project.objects.filter(pk=pk).exists():
            # If the instance doesn't exist in the database, save it
            try:
                instance.save()
                msg = "Se ha creado un proyecto nuevo"
                save_in_history(pk, 2, msg)  # Use type 2 for creation
                prev = request.META.get('HTTP_REFERER')
                return redirect(prev)
            except Exception as e:
                print(f"Error saving new project: {str(e)}")
                
        instance.save()
        if msg == "":
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
@login_required
def history_view(request):
    history = Event.objects.order_by('-time')[:100]
    grouped_objects_def = defaultdict(lambda: defaultdict(list))
    for h in history:
        h.link = False
        if Project.objects.filter(pk=h.model_pk).exists():
            h.link = True
        year = h.time.year
        month = h.time.month
        print(h.link)
        grouped_objects_def[year][month].append(h)
        
    for obj in grouped_objects_def:
       grouped_objects_def[obj].default_factory = None
    grouped_objects = dict(grouped_objects_def)
    return render (request, 'history_template.html', {'yearlist':grouped_objects})

#Modulo de busqueda
def search(request):
    try:
        query = request.GET.get('query')  # Get the search query from the request
        # Perform your search logic here and get the results
        if query:
            objectc = Project.objects.filter(
                    Q(client__name__icontains=query) | Q(partida__icontains=query)
                ).order_by('-created')[:5]
            results = []
            for obj in objectc:
                results.append({
                'id': obj.pk,
                'type': obj.type,
                'datecreated': obj.created.strftime('%d/%m/%Y'),
                })
        else:
            results = list(Project.objects.none())
    
        return JsonResponse({'results': results}, safe=False)
    except DatabaseError as e:
       # Log the error if you want
       logger.error(f"Database error in search view: {str(e)}")
       return JsonResponse({'error': 'Database error occurred.'}, status=500)
    except Exception as e:
       logger.error(f"Unexpected error in search view: {str(e)}")
       return JsonResponse({'error': 'An unexpected error occurred.'}, status=500)

#Modulo descargas
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

#Modulo de subida de archivos
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

#Modulo de eliminacion de archivos
def delete_file(request, pk):
    file = ProjectFiles.objects.get(project_pk=pk)
    bucket_name = os.getenv('SUPABASE_BUCKET')
    supabase.storage.from_(bucket_name).remove([file.name])
    file.delete()
    prev = request.META.get('HTTP_REFERER')
    return redirect(prev)

#Modulo de vista de archivos
def file_view(request, pk):
    files = ProjectFiles.objects.filter(project_pk = pk)
    
    return render (request, 'files_template.html', {'files':files})   

#Creacion de cliente
def create_client_view(request):
    if request.method == 'POST':
        if request.POST.get('name') != '':
            client = Client.objects.create(name=request.POST.get('name'), phone=request.POST.get('phone'), flag = True)
            client.save() 
            return redirect('clients')
    return render (request, 'create_client_template.html')

#Vista de clientes
def clients_view(request):
    if request.method == 'POST':
        if request.POST.get('client-name') != '':
            client = Client.objects.create(name=request.POST.get('client-name'), phone=request.POST.get('client-phone'))
            client.save()
            return redirect('clients')
    if request.GET.get('flagc') != "":
        query = request.GET.get('flagc')
        if query == 'True':
            flag= True
            clients = Client.objects.filter(flag=flag).order_by('name')
        else:
            flag= False
            clients = Client.objects.filter(flag=flag).order_by('name')
        context = {'clients': clients, 'flag': flag}
        return render (request, 'clients_template.html', context)
    return render (request, 'clients_template.html', {'clients':clients})

#Creacion de proyecto a partir de un cliente
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

#Remover un cliente de la lista de clientes en formulario de creacion
def clientedislist(request, pk):
    client = Client.objects.get(pk=pk)
    client.not_listed = True
    client.save()
    return redirect('clients')