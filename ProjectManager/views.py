from django.conf import settings

from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.core.paginator import Paginator, PageNotAnInteger
from Accounting.models import Account, MonthlyFinancialSummary
from .forms import ProjectForm, FileFieldForm, ProjectFullForm
from .models import Project, Client, Event, ProjectFiles
from django.db.models import Q, Sum, Count
from django.db.models.functions import ExtractMonth
from decimal import Decimal as Dec
from datetime import datetime
import time
from .functions import month_str
from collections import defaultdict
from .supabase_client import supabase
import logging
logger = logging.getLogger(__name__)
from django.http import FileResponse
from django.contrib.auth.decorators import login_required
import io
from urllib.request import urlopen
from urllib.error import URLError
from django.db import DatabaseError, transaction
from Accounting.views import create_acc_entry, create_account, get_earnings_per_client

#Manejo de paginacion
def paginate_queryset(request: HttpRequest, queryset, per_page=12) -> tuple: 
    """Paginate any queryset and handle pagination errors"""
    num_page = request.GET.get('page')
    paginator = Paginator(queryset, per_page)
    try:
        page_obj = paginator.get_page(num_page)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    return page_obj, paginator

#Vista principal
@login_required
def index(request):
    return render (request, 'Index.html')

#chart data format
def chart_data_format(data: dict) -> dict:
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
def chart_data(request: HttpRequest) -> JsonResponse:
    try:
        if request.method == 'POST':
            # Try to get date from POST data
            date = request.POST.get('date')       
            # If we got a date and it's in YYYY-MM format
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

            
        month_summary = MonthlyFinancialSummary.objects.filter(year=year, month=month).first()
        total_estimated = 0
        sums = Account.objects.filter(
            project__created__month=month, 
            project__created__year=year
        ).aggregate(
            total_estimated=Sum('estimated')
        )
        total_estimated = sums['total_estimated'] or 0
    
        
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
def generate_month_data(months: list, year: list) -> tuple[list, list]:
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    for y in range(2023, current_year + 1):
        year.append({'year':y})
        end_month = 12 if y < current_year else current_month
        for m in range(1, end_month + 1):
            months.append({'year': y, 'month': m})

    return months, year

#add a delete project function
@transaction.atomic
def delete_view(request: HttpRequest, pk: int) -> HttpResponse:
    try:
        if request.method == 'POST':
            project = Project.objects.select_related('client').get(pk=pk)
            msg = "Se ha eliminado un proyecto " + project.type + " de " + project.client.name
        
            Event.objects.filter(model_pk=pk).delete()
            file = ProjectFiles.objects.filter(project_pk=pk).first()
            if file:
                delete_file(request, pk)
            project.delete()
            save_in_history(pk, 3, msg)
        return redirect('index')
    except Project.DoesNotExist:
        logger.error(f"Project with pk {pk} does not exist.")
        return redirect('index')

#Archivado de proyectos
@transaction.atomic
def close_view(request: HttpRequest, pk: int) -> HttpResponse:
    try:
        project = Project.objects.get(pk=pk)
        project.closed = True
        project.paused = False
        project.save()
        msg = "Se ha cerrado un proyecto"
        save_in_history(pk, 1, msg)
        return redirect('projects')
    except Project.DoesNotExist:
        logger.error(f"Project with pk {pk} does not exist.")
        return redirect('projects')

@transaction.atomic
def pause_view(request: HttpRequest, pk: int) -> HttpResponse:
    try:
        project = Project.objects.get(pk=pk)
        if project.paused:
            # If already paused, resume it
            project.paused = False
            msg = "Se ha reanudado un proyecto"
        else:
            project.paused = True
            msg = "Se ha pausado un proyecto"
        project.save()
        save_in_history(pk, 1, msg)
        return redirect('projects')
    except Project.DoesNotExist:
        logger.error(f"Project with pk {pk} does not exist.")
        return redirect('projects')


#Formateo de datos
def format_currency(value):
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

#Obtengo los datos financieros
def get_financial_data(year: int, month: int) -> dict:
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
    
    if not monthly_summary:
        # Return empty but valid data structure when no data exists
        data.update({
            'raw': {
                'total': Dec('0.00'),
                'estimated': Dec('0.00'),  # Added for chart_data_format
                'adv': Dec('0.00'),
                'advance': Dec('0.00'),   # Added for chart_data_format
                'pending': Dec('0.00'),
                'exp': Dec('0.00'),
                'expenses': Dec('0.00'),  # Added for chart_data_format
                'net': Dec('0.00'),
                'net_by_type': {         # Added for chart_data_format
                    'estado_parcelario': Dec('0.00'),
                    'amojonamiento': Dec('0.00'),
                    'relevamiento': Dec('0.00'),
                    'mensura': Dec('0.00'),
                    'legajo_parcelario': Dec('0.00')
                }
            },
            'formatted': {
                'total': format_currency(Dec('0.00')),
                'adv': format_currency(Dec('0.00')),
                'pending': format_currency(Dec('0.00')),
                'exp': format_currency(Dec('0.00')),
                'net': format_currency(Dec('0.00'))
            },
            'counts': {
                'total': 0,
                'current_month': 0,
                'previous_months': 0
            }
        })
        return data
    
    # 2. Get projects (single query) - include ALL projects for the month/year
    projects = Project.objects.filter(created__month=month, created__year=year)
    data['objects']['projects'] = projects
    
    # 3. Get accounts (single query)
    accounts = Account.objects.filter(project__created__month=month, project__created__year=year)
    data['objects']['accounts'] = accounts
    # 4. Calculate all values once
    if monthly_summary:
        adv = monthly_summary.total_advance or 0
        exp = monthly_summary.total_expenses or 0
        net = monthly_summary.net_worth() or 0
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
        'adv': adv,           # Keep consistent naming
        'advance': adv,       # For chart_data_format compatibility
        'exp': exp,           # Keep consistent naming  
        'expenses': exp,      # For chart_data_format compatibility
        'net': net,
        'networth': net,
        'total': total_estimated,
        'estimated': total_estimated,  # For chart_data_format compatibility
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
    current_date = datetime.now()
    current_year = current_date.year
    current_month_num = current_date.month
    
    data['counts'] = {
        'total': projects.count(),                    # Total projects for the requested month
        'current_month': Project.objects.filter(     # Projects created in the actual current month
            created__year=current_year, 
            created__month=current_month_num
        ).count(),
        'previous_months': Project.objects.filter(
            closed=False, 
            paused=False
        ).exclude(
            created__year=year, 
            created__month=month
        ).count(),
    }
    
    return data

#Funcion usada dentro de balance, para mostrar el balance anual
def balance_anual(year: int) -> tuple[list, list]:
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
def balance(request: HttpRequest) -> HttpResponse:
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
        clients_ctx = get_earnings_per_client(5)

    except Exception as e:
        # Manejo de errores
        print(f"Error al obtener datos financieros: {e}")
        return render (request, 'balance_template.html', {'non_exist':True})

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
        'clients_ctx': clients_ctx,
    })
@login_required
def list_paused(request: HttpRequest) -> HttpResponse:
    """
    List all paused projects.
    """
    projects = Project.objects.select_related('client').filter(paused=True).order_by('-created')[:108]
    if not projects.exists():
        return render(request, 'project_list_template.html', {'no_projects': True})
    
    actual_pag, pages = paginate_queryset(request, projects)
    return render(request, 'project_list_template.html', {'projects': actual_pag, 'pages': pages})

@login_required
def list_closed(request: HttpRequest) -> HttpResponse:
    """
    List all closed projects.
    """
    projects = Project.objects.select_related('client').filter(closed=True).order_by('-created')[:108]
    if not projects.exists():
        return render(request, 'project_list_template.html', {'no_projects': True})
    
    actual_pag, pages = paginate_queryset(request, projects)
    return render(request, 'project_list_template.html', {'projects': actual_pag, 'pages': pages})

    
#Todos los proyectos
@login_required
def projectlist_view(request: HttpRequest) -> HttpResponse:
    # Get view mode from GET parameter (default to 'cards')
    view_mode = request.GET.get('view', 'cards')
    
    if request.method == 'POST':
        if request.POST.get('search-input')!="":
            query = request.POST.get('search-input')
            projects = Project.objects.select_related('client').filter(
                 Q(client__name__icontains=query) | Q(partido__icontains=query)
            ).order_by('-created')[:108]
            
            if not projects.exists():
                return render (request, 'project_list_template.html', {'no_projects':True, 'view_mode': view_mode})
        actual_pag, pages = paginate_queryset(request, projects)
        return render (request, 'project_list_template.html', {'projects':actual_pag, 'pages':pages, 'view_mode': view_mode})
        
    else:
        actual_pag, pages = paginate_queryset(request, Project.objects.select_related('client').filter(closed=False, paused=False).order_by('-created')[:108])
    return render (request, 'project_list_template.html', {'projects':actual_pag, 'pages':pages, 'view_mode': view_mode})

#Proyectos por cliente
@login_required
def alt_projectlist_view(request: HttpRequest, pk: int) -> HttpResponse:
    view_mode = request.GET.get('view', 'cards')
    projects = Project.objects.select_related('client').filter(client__pk=pk).order_by('-created')[:108]
    if not projects.exists():
        return render (request, 'project_list_template.html', {'no_projects':True, 'view_mode': view_mode})
    actual_pag, pages = paginate_queryset(request, projects)
    return render (request, 'project_list_template.html', {'projects':actual_pag, 'pages':pages, 'view_mode': view_mode})

#Proyectos por tipo
@login_required
def projectlistfortype_view(request: HttpRequest, type: int) -> HttpResponse:
    #Mensuras
    type_map = {
        1: "Mensura",
        2: "Estado Parcelario",
        3: "Amojonamiento",
        4: "Relevamiento",
        5: "Legajo Parcelario"
    }
    project_type = type_map.get(type)
    if not project_type:
        return render(request, 'project_list_template.html', {'no_projects': True})
    projects = Project.objects.select_related('client').filter(type=project_type, closed=False, paused=False).order_by('-created')[:108]
    actual_pag, pages = paginate_queryset(request, projects)
    if not projects.exists():
        return render (request, 'project_list_template.html', {'no_projects':True})
    return render (request, 'project_list_template.html', {'projects':actual_pag, 'pages':pages})

#Vista de un proyecto
@login_required
def project_view(request: HttpRequest, pk: int) -> HttpResponse:
    try:
        project = Project.objects.get(pk=pk)
        file = ProjectFiles.objects.filter(project_pk=pk).first()
        if file:
            return render(request, 'project_template.html', {'project': project, 'file_url': file.url})
        else:
            form = FileFieldForm()
        return render(request, 'project_template.html', {'project': project, 'form': form})
    except Project.DoesNotExist:
        logger.error(f"Project with ID {pk} does not exist.")
        return redirect('projects')

#Registro en historial
def save_in_history(pk: int, type: int, msg: str):
    event = Event.objects.create(model_pk=pk, type=type, msg=msg)

#Vista formulario de creacion
@login_required
def create_view(request: HttpRequest) -> HttpResponse:
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
                form_instance.created_by = request.user  # Asigna el usuario actual
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
@transaction.atomic
def mod_view(request: HttpRequest, pk: int) -> HttpResponse:
    if request.method == 'POST':
        try:
            instance = Project.objects.select_related('client').get(pk=pk)
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
        
                
            instance.save()
            if msg == "":
                msg = "Se ha modificado un proyecto"
            pk = instance.pk
            save_in_history(pk, 1, msg)
            prev = request.META.get('HTTP_REFERER')
            return redirect(prev)
        except Project.DoesNotExist:
            logger.error(f"Project with pk {pk} does not exist.")
            return render(request, 'mod_template.html', {'error': 'Project not found.'})
        except Exception as e:
            logger.error(f"Error updating: {str(e)}")
            return render(request, 'mod_template.html', {'error': 'Error saving project.'})

    prev = request.META.get('HTTP_REFERER')
    return redirect(prev)

#Modificacion total del proyecto
@login_required
@transaction.atomic
def full_mod_view(request: HttpRequest, pk: int) -> HttpResponse:
    if request.method == 'POST':
        instance = Project.objects.get(pk=pk)
        form = ProjectFullForm(request.POST, instance=instance) 
        if form.is_valid():
            try:
                form.save()
                msg = "Se ha modificado un proyecto"   
                save_in_history(instance.pk, 1, msg)
                return redirect('projectview', pk=pk)
            except Exception as e:
                logger.error(f"Error saving full project modification: {str(e)}")
                return render(request, 'full_mod_template.html', {'error': 'Error saving project.'})
    else:
        instance = Project.objects.get(pk=pk)
        form = ProjectFullForm(instance=instance)
    return render (request, 'full_mod_template.html', {'form':form, 'project':instance})

#Vista de historial
@login_required
def history_view(request: HttpRequest) -> HttpResponse:
    events = Event.objects.order_by('-time')[:100]
    grouped_objects_def = defaultdict(lambda: defaultdict(list))
    for e in events:
        #Si es un type 3 (eliminacion) no hay link
        if e.type == 3:
            e.link = False
        else:
            e.link = True
        year = e.time.year
        month = e.time.month
        grouped_objects_def[year][month].append(e)

    for obj in grouped_objects_def:
       grouped_objects_def[obj].default_factory = None
    grouped_objects = dict(grouped_objects_def)
    return render (request, 'history_template.html', {'yearlist':grouped_objects})

#Modulo de busqueda
@login_required
def search(request: HttpRequest) -> JsonResponse:
    try:
        query = request.GET.get('query')  # Get the search query from the request
        # Perform your search logic here and get the results
        if query:
            objectc = Project.objects.select_related('client').filter(
                    Q(client__name__icontains=query) | Q(partida__icontains=query)
                ).order_by('-created')[:5]
            results = []
            for obj in objectc:
                results.append({
                'id': obj.pk,
                'type': obj.type,
                'datecreated': obj.created.strftime('%d/%m/%Y'),
                'client': obj.client.name if obj.client else 'Sin Cliente',
                'partida': obj.partida if obj.partida else 'Sin Partida',
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
def download_file(request: HttpRequest, pk: int) -> HttpResponse:
    file = ProjectFiles.objects.get(project_pk=pk)
    file_name = file.name
    bucket_name = settings.SUPABASE_BUCKET
    
    file_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
    try:
        response = urlopen(file_url)
        file_content = io.BytesIO(response.read())
        return FileResponse(file_content, as_attachment=True, filename=file_name)
    except URLError as e:
        logger.error(f"Error downloading file: {str(e)}")
        return JsonResponse({'error': 'Failed to download file'}, status=500)

#Modulo de subida de archivos
@transaction.atomic
def upload_files(request: HttpRequest, pk: int) -> HttpResponse:
    if request.method == 'POST':
        form = FileFieldForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                file = request.FILES['file_field']
                timestamp = int(time.time())
                file_name = f"{pk}_{timestamp}_{file.name}"
                bucket_name = settings.SUPABASE_BUCKET
                with file.open() as file_content:
                   supabase.storage.from_(bucket_name).upload(file_name, file_content)
                file_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
                ProjectFiles.objects.create(project_pk=pk, name=file_name, url=file_url)
            except Exception as e:
                logger.error(f"Error uploading file for project {pk}: {str(e)}")
                
    prev = request.META.get('HTTP_REFERER')
    return redirect(prev)

#Modulo de eliminacion de archivos
@transaction.atomic
def delete_file(request: HttpRequest, pk: int) -> HttpResponse:
    try:
        file = ProjectFiles.objects.get(project_pk=pk)
        bucket_name = settings.SUPABASE_BUCKET
        supabase.storage.from_(bucket_name).remove([file.name])
        file.delete()
        prev = request.META.get('HTTP_REFERER')
        return redirect(prev)
    except Exception as e:
        logger.error(f"Error deleting file for project {pk}: {str(e)}")
        
#Modulo de vista de archivos
def file_view(request: HttpRequest, pk: int) -> HttpResponse:
    files = ProjectFiles.objects.filter(project_pk=pk)
    return render(request, 'files_template.html', {'files': files})

#Creacion de cliente
@transaction.atomic
def create_client_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        if request.POST.get('name') != '':
            try:
                client = Client.objects.create(name=request.POST.get('name'), phone=request.POST.get('phone'), flag = True)
                client.save() 
                return redirect('clients')
            except Exception as e:
                logger.error(f"Error creating client: {str(e)}")
                return render(request, 'create_client_template.html', {'error': 'Error creating client.'})
    return render (request, 'create_client_template.html')

#Vista de clientes
@login_required
@transaction.atomic
def clients_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        try:
            if request.POST.get('client-name') != '':
                client = Client.objects.create(name=request.POST.get('client-name'), phone=request.POST.get('client-phone'))
                client.save()
            return redirect('clients')
        except Exception as e:
            logger.error(f"Error creating client: {str(e)}")
            return render(request, 'clients_template.html', {'error': 'Error creating client.'})    
    if request.GET.get('flagc') != "":
        query = request.GET.get('flagc')
        if query == 'True':
            flag= True
            clients = Client.objects.filter(flag=flag).only('id', 'name', 'phone').order_by('name')
        else:
            flag= False
            clients = Client.objects.filter(flag=flag).only('id', 'name', 'phone').order_by('name')
        context = {'clients': clients, 'flag': flag}
        return render (request, 'clients_template.html', context)
    return render (request, 'clients_template.html', {'clients':clients})

#Creacion de proyecto a partir de un cliente
@login_required
@transaction.atomic
def create_for_client(request: HttpRequest, pk: int) -> HttpResponse:
    if request.method == 'POST':
        form = ProjectForm(request.POST)    
        if form.is_valid():
            try:
                form_instance = form.save(commit=False)
                form_instance.client = Client.objects.get(pk=pk)
                form_instance.created_by = request.user  # Asigna el usuario actual
                form_instance.save()#Se guarda la instancia 
                msg = "Se ha creado un nuevo proyecto"   
                save_in_history(pk, 2, msg)
                create_account(form_instance.pk)
                if 'save_and_backhome' in request.POST:
                    
                    return redirect('projectview', pk=form_instance.pk)
            except Exception as e:
                logger.error(f"Error creating project for client {pk}: {str(e)}")
                return render(request, 'project_for_client.html', {'error': 'Error creating project.'})    
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
def clientedislist(request: HttpRequest, pk: int) -> HttpResponse:
    client = Client.objects.get(pk=pk)
    client.not_listed = True
    client.save()
    return redirect('clients')

# Add this new function to handle balance info requests
@login_required
def balance_info(request: HttpRequest) -> JsonResponse:
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
        if balance_data is False:
            return JsonResponse({'error': 'No financial data found for the specified month and year.'}, status=404)
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