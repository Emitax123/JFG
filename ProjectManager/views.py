from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator, PageNotAnInteger

from Accounting.models import Account, MonthlyFinancialSummary
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

#chart data format
def chart_data_format(data):
    """
    Format data for chart visualization.
    This function processes raw financial data into a structured format suitable for 
    rendering charts, specifically doughnut charts. It organizes data into two main categories:
    balance information (total, collection, expenses) and revenue by service type.
    Parameters:
    -----------
    data : dict
        A dictionary containing financial data with a 'raw' key that includes:
        - 'estimated': Total estimated revenue
        - 'advance': Amount collected/advanced
        - 'expenses': Total expenses
        - 'net_by_type': Dictionary with revenue breakdown by service type:
            - 'estado_parcelario': Revenue from property status services
            - 'amojonamiento': Revenue from boundary marking services
            - 'relevamiento': Revenue from surveying services
            - 'mensura': Revenue from measurement services
            - 'legajo_parcelario': Revenue from property file services
    Returns:
    --------
    dict
        A formatted dictionary containing:
        - 'label1', 'label2': Chart titles/labels
        - 'labels1', 'labels2': Category labels for the two chart types
        - 'values1', 'values2': Corresponding numerical values for each category
        - 'chart_type': The type of chart to render (doughnut)
        - 'barckgroundColor', 'barckgroundColor2': Color schemes for the charts
    """
    
    chart_data = {
        'label1': 'Balance',
        'label2': 'Ganancias por tipo',
        'labels1': ['Total', 'Cobro', 'Gastos'],
        'values1': [
            float(data['raw']['estimated']), 
            float(data['raw']['advance']), 
            float(data['raw']['expenses'])
        ],
        'labels2': ['Est.Parcelario', 'Amojonamiento', 'Relevamiento', 'Mensura', 'Legajo Parcelario'],
        'values2': [
            float(data['raw']['net_by_type']['estado_parcelario']),
            float(data['raw']['net_by_type']['amojonamiento']),
            float(data['raw']['net_by_type']['relevamiento']),
            float(data['raw']['net_by_type']['mensura']),
            float(data['raw']['net_by_type']['legajo_parcelario'])
        ],
        'chart_type': 'doughnut',
        'barckgroundColor': ['red', 'blue', 'green'],
        'barckgroundColor2': ['red', 'blue', 'green', 'orange', 'purple']
    }
    return chart_data

# charts/views.py
def chart_data(request):
    print(f"====== Chart Data Request ======")
    print(f"Request method: {request.method}")
    
    try:
        if request.method == 'POST':
            # Check all possible sources of data
            print(f"POST data: {request.POST}")
            print(f"POST body: {request.body[:100] if request.body else 'Empty'}")
            
            # Try to get date from POST data
            date = request.POST.get('date')
            print(f"Date from POST: {date}")
            
            # If we got a date and it's in YYYY-MM format
            if date and '-' in date:
                try:
                    date_split = date.split("-")
                    if len(date_split) >= 2:
                        month = int(date_split[1])
                        year = int(date_split[0])
                        print(f"Successfully parsed date: month={month}, year={year}")
                    else:
                        raise ValueError(f"Invalid date format: {date}")
                except Exception as e:
                    print(f"Error parsing date: {e}")
                    month = datetime.now().month
                    year = datetime.now().year
            else:
                print("No valid date in POST, using current date")
                month = datetime.now().month
                year = datetime.now().year
        else:
            month = datetime.now().month
            year = datetime.now().year

            
        month_summary = MonthlyFinancialSummary.objects.filter(year=year, month=month).first()
        accounts = Account.objects.filter(project__created__month=month, project__created__year=year)
        
        if accounts.exists():
            sums = accounts.aggregate(
                total_estimated=Sum('estimated'),
            )
            total_estimated = sums['total_estimated'] or 0
        else:
            total_estimated = 0
           

        if month_summary:
            total_advance = month_summary.total_advance or 0
            total_expenses = month_summary.total_expenses or 0
            net_estado_parcelario = month_summary.total_net_est_parc or 0
            net_mensura = month_summary.total_net_mensura or 0
            net_amojonamiento = month_summary.total_net_amoj or 0
            net_relevamiento = month_summary.total_net_relev or 0
            net_legajo_parcelario = month_summary.total_net_leg or 0
        else:
            total_advance = 0
            total_expenses = 0
            net_estado_parcelario = 0
            net_mensura = 0
            net_amojonamiento = 0
            net_relevamiento = 0
            net_legajo_parcelario = 0
    except Exception as e:
        print(f"Error in chart_data: {e}")
        # Fall back to default values if there's an error
        total_advance = 0
        total_expenses = 0
        net_estado_parcelario = 0
        net_mensura = 0
        net_amojonamiento = 0
        net_relevamiento = 0
        net_legajo_parcelario = 0
        
    
    labels = ['Total', 'Cobro', 'Gastos']
    values = [total_estimated, total_advance, total_expenses]
    backg = ['red', 'blue', 'green']

   

    # Annotate each project with its net price

    # Aggregate net price by type

    # Ensure all variables are always defined, even if not present in net_by_type
   
    

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



def get_financial_data(year, month):
    """
    Single function to retrieve all financial data needed for both
    balance and chart displays.
    """
    data = {
        'raw': {},
        'formatted': {},
        'counts': {},
        'objects': {},
    }
    
    # 1. Get monthly summary (single query)
    monthly_summary = MonthlyFinancialSummary.objects.filter(year=year, month=month).first()
    data['objects']['monthly_summary'] = monthly_summary
    
    # 2. Get projects (single query)
    projects = Project.objects.filter(created__month=month, created__year=year).exclude(
        price=None, adv=None, gasto=None
    )
    data['objects']['projects'] = projects
    
    # 3. Get accounts (single query)
    accounts = Account.objects.filter(project__created__month=month, project__created__year=year)
    data['objects']['accounts'] = accounts
    
    # 4. Calculate all values once
    if monthly_summary:
        adv = monthly_summary.total_advance or 0
        exp = monthly_summary.total_expenses or 0
        net = monthly_summary.total_networth or 0
        net_estado_parcelario = monthly_summary.total_net_est_parc or 0
        net_mensura = monthly_summary.total_net_mensura or 0
        net_amojonamiento = monthly_summary.total_net_amoj or 0
        net_relevamiento = monthly_summary.total_net_relev or 0
        net_legajo_parcelario = monthly_summary.total_net_leg or 0
    else:
        adv = exp = net = 0
        net_estado_parcelario = net_mensura = net_amojonamiento = 0
        net_relevamiento = net_legajo_parcelario = 0
    
    # 5. Calculate estimated amount (single aggregation)
    sums = projects.aggregate(total=Sum('price'))
    total_estimated = sums['total'] or 0
    
    # Store raw values
    data['raw'] = {
        'advance': adv,
        'expenses': exp,
        'networth': net,
        'estimated': total_estimated,
        'pending': total_estimated - adv - exp,
        'net_by_type': {
            'estado_parcelario': net_estado_parcelario,
            'mensura': net_mensura,
            'amojonamiento': net_amojonamiento,
            'relevamiento': net_relevamiento,
            'legajo_parcelario': net_legajo_parcelario,
        }
    }
    
    # Store formatted values
    data['formatted'] = {
        'adv': format_currency(adv),
        'exp': format_currency(exp),
        'net': format_currency(net),
        'total': format_currency(total_estimated),
        'pending': format_currency(total_estimated - adv - exp),
    }
    
    # Store counts
    data['counts'] = {
        'total': projects.count(),
        'current_month': projects.filter(created__month=month).count(),
        
        'previous_months': Project.objects.filter(closed=False).exclude(
            Q(created__year=year, created__month=month)
        ).exclude(price=None, adv=None, gasto=None).count(),
    }
    
    return data
#Funcion usada dentro de balance, para mostrar el balance anual
def balance_anual(year):
    # Annotate each project with its month
    
    year_summary = MonthlyFinancialSummary.objects.filter(year=year).order_by('month')
    # Create a dictionary to easily look up summaries by month
    summary_by_month = {summary.month: summary for summary in year_summary}
    
    # Pre-fetch all project counts for the year to avoid multiple queries
    project_counts = {}
    for month_data in Project.objects.filter(created__year=year).annotate(
        month=ExtractMonth('created')
    ).values('month').annotate(count=Count('id')):
        project_counts[month_data['month']] = month_data['count']
    
    monthly_totals = []
    year_networth = 0
    for month_num in range(1, 13):
        # Get the summary for the current month, or create a default one if it doesn't exist
        month_name = month_str(month_num)
        if month_num in summary_by_month:
            #Find data for month, because it exists
            summary = summary_by_month[month_num]
            
            monthly_totals.append({
                'month': month_str(summary.month),
                'total_networth': format_currency(summary.total_networth),
                'project_count': project_counts.get(month_num, 0)
            })
            year_networth += summary.total_networth
        else:
            # If no summary exists for this month, create a default one
            monthly_totals.append({
                'month': month_name,
                'total_networth': format_currency(0),
                'project_count': project_counts.get(month_num, 0)
            })
    return monthly_totals, format_currency(year_networth)

   

#Balance
@login_required
def balance(request):
    method_post = False
    if request.method == 'POST':
        method_post = True
        #Aqui el user selecciona el mes y año
        date = request.POST.get('date')
        date_split = date.split("-")
        month = int(date_split[1])
        year = int(date_split[0])
       

    else:
        #Si no selecciona nada, se toma el mes y año actual
        month = datetime.now().month
        year = datetime.now().year
        #Obtengo los proyectos del mes y año actual, pero solo los que no estan cerrados
    try:
        balance_data = get_financial_data(year, month)
        data, year_total = balance_anual(year)
        chart_data = chart_data_format(balance_data)
        
    except Exception as e:
        # Manejo de errores
        print(f"Error al obtener datos financieros: {e}")
        return render (request, 'error_template.html', {'non_exist':True})

    return render (request, 'balance_template.html', {
        'method_post':method_post,
        'total':balance_data['formatted']['total'], 
        'adv':balance_data['formatted']['adv'], 
        'pending':balance_data['formatted']['pending'],
        'cant':balance_data['counts']['total'],
        'cant_actual_month':balance_data['counts']['current_month'],
        'cant_previus_months':balance_data['counts']['previous_months'],
        'gastos':balance_data['formatted']['exp'], 
        'net':balance_data['formatted']['net'],
        'month':month_str(month),
        'month_number': month,  # Pass the numeric month as well 
        'year':year,
        'monthly_totals': data,
        'neto_anual': year_total,
        'chart_data': chart_data,
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
                newadv_asdecimal = Dec(request.POST.get('adv'))
                previous_adv = instance.adv
                instance.adv = instance.adv + newadv_asdecimal
                if newadv_asdecimal < 0:
                    msg = "Se devolvieron $" + str(abs(newadv_asdecimal)) + " del proyecto " + str(instance.pk)
                else:
                    msg = "Se cobraron $" + str(newadv_asdecimal) + " del proyecto " + str(instance.pk)
                create_acc_entry(instance.pk, 'adv', previous_adv, newadv_asdecimal)
            except:
                instance.adv = Dec("0.00")
        if request.POST.get('gasto'):
            try:
                newgasto_asdecimal = Dec(request.POST.get('gasto'))
                previous_gasto = instance.gasto or Dec("0.00")
                instance.gasto = instance.gasto + newgasto_asdecimal
                if newgasto_asdecimal < 0:
                    msg = "Se redujo $" + str(abs(newgasto_asdecimal)) + " el gasto del proyecto " + str(instance.pk)
                else:
                    msg = "Se debitaron $" + str(newgasto_asdecimal) + " al proyecto " + str(instance.pk)
                create_acc_entry(instance.pk, 'exp', previous_gasto, newgasto_asdecimal)
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

# Add this new function to handle balance info requests
def balance_info(request):
    """
    Return balance information for AJAX requests.
    
    Args:
        request: HTTP request containing date information.
        
    Returns:
        JsonResponse: Balance information data in JSON format.
    """
    try:
        if request.method == 'POST':
            date = request.POST.get('date')
            if date and '-' in date:
                try:
                    date_split = date.split("-")
                    if len(date_split) >= 2:
                        month = int(date_split[1])
                        year = int(date_split[0])
                    else:
                        raise ValueError(f"Invalid date format: {date}")
                except Exception as e:
                    month = datetime.now().month
                    year = datetime.now().year
            else:
                month = datetime.now().month
                year = datetime.now().year
        else:
            month = datetime.now().month
            year = datetime.now().year
        
        # Use the existing function to get financial data
        balance_data = get_financial_data(year, month)
        
        # Format the data for the response
        response_data = {
            'balance_info': {
                'month': month_str(month),
                'year': year,
                'total': balance_data['formatted']['total'],
                'adv': balance_data['formatted']['adv'],
                'pending': balance_data['formatted']['pending'],
                'cant_actual_month': balance_data['counts']['current_month'],
                'cant_previus_months': balance_data['counts']['previous_months'],
                'gastos': balance_data['formatted']['exp'],
                'net': balance_data['formatted']['net']
            }
        }
        
        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)