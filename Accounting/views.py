from decimal import Decimal
from typing import Optional
import logging
logger = logging.getLogger(__name__)
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Account, AccountMovement, MonthlyFinancialSummary
from ProjectManager.models import Client
from ProjectManager.models import Project
from django.db import transaction
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import F, Sum, Count
from django.contrib.auth.decorators import login_required
from .forms import ManualAccountEntryForm
# Removed circular import: from ProjectManager.views import format_currency

# Utility function moved here to avoid circular import
def format_currency(value):
    """Format currency with proper decimal and thousands separators"""
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Create your views here.

def create_account(project_id: int) -> Account: 
    """
    Create an account for a project if it does not already exist.
    """
    # Search or crates an account for the given project_id.
    try:
        project = Project.objects.get(id=project_id)
        account, created = Account.objects.get_or_create(project=project)
        if created:
            print(f"Account created for project {project_id}")
        else:
            print(f"Account already exists for project {project_id}")
        return account
    except Project.DoesNotExist:
        print(f"Project with id {project_id} does not exist.")
        return None

def create_acc_entry(project_id: int, 
                     field: str, 
                     old_value: Decimal, 
                     new_value: Decimal,
                     custom_description: str = None
                     ) -> Optional[Account]:
    """
    Create an account entry for a project when a field is updated.
     Args:
        project_id: The ID of the project.
        field: The field being updated ('adv', 'exp', or 'est').
        old_value: The previous value.
        new_value: The new value.
        
    Returns:
        The updated account object, or None if the operation failed.
    """
    # Ensure we're working with Decimal objects to avoid type errors
    if old_value is None:
        old_value = Decimal('0.00')
    elif not isinstance(old_value, Decimal):
        try:
            old_value = Decimal(str(old_value))
        except:
            old_value = Decimal('0.00')
            
    if new_value is None:
        new_value = Decimal('0.00')
    elif not isinstance(new_value, Decimal):
        try:
            new_value = Decimal(str(new_value))
        except:
            new_value = Decimal('0.00')
    
    print(f"Processing: project_id={project_id}, field={field}, old_value={old_value}, new_value={new_value}")
    
    try:
        with transaction.atomic():
            # Get project
            project = Project.objects.get(id=project_id)
            print(f"Found project: {project}")
            
            # Get or create account (simplified to avoid redundancy)
            account, created = Account.objects.get_or_create(project=project)
            print(f"{'Created new' if created else 'Using existing'} account for project {project_id}")
            
            # Get or create the monthly summary - asignar usuario del proyecto
            current_year = int(timezone.now().year)
            current_month = int(timezone.now().month)
            
            monthly_summary, createdm = MonthlyFinancialSummary.objects.get_or_create(
                year=current_year,
                month=current_month,
                created_by=project.created_by,  # Usar el created_by del proyecto
                defaults={
                    'total_advance': Decimal('0.00'),
                    'total_expenses': Decimal('0.00'),
                    'total_networth': Decimal('0.00'),  # Add this field to defaults
                    'total_net_mensura': Decimal('0.00'),
                    'total_net_est_parc': Decimal('0.00'),
                    'total_net_leg': Decimal('0.00'),
                    'total_net_amoj': Decimal('0.00'),
                    'total_net_relev': Decimal('0.00'),
                }
            )
            if createdm:
                print(f"Monthly summary created for {current_year}-{current_month}")
            else:
                print(f"Using existing monthly summary for {current_year}-{current_month}")
            
            # Process based on field type
            if field == 'adv':
                # Update Account
                if created:
                    # For new accounts, set the initial value directly
                    Account.objects.filter(id=account.id).update(advance=new_value)
                else:
                    # For existing accounts, add to current value
                    Account.objects.filter(id=account.id).update(advance=F('advance') + new_value)
                
                # Update Project - add to existing advance value
                Project.objects.filter(id=project_id).update(adv=F('adv') + new_value)
                
                # Update MonthlyFinancialSummary
                if createdm:
                    # For new monthly summaries, set the initial value directly
                    MonthlyFinancialSummary.objects.filter(id=monthly_summary.id).update(total_advance=new_value)
                else:
                    # For existing summaries, add to current value
                    MonthlyFinancialSummary.objects.filter(id=monthly_summary.id).update(total_advance=F('total_advance') + new_value)
                
                define_type_for_summary(monthly_summary, project.type, new_value, createdm)
                if new_value < 0:
                    acc_mov_description = f"Se devolvieron ${abs(new_value)}"
                else:
                    acc_mov_description = f"Se cobraron ${new_value}"
                    
            elif field == 'exp':
                print(f"Monthly expenses before update: {monthly_summary.total_expenses}")
                
                # Update Account
                if created:
                    # For new accounts, set the initial value directly
                    Account.objects.filter(id=account.id).update(expenses=new_value)
                else:
                    # For existing accounts, add to current value
                    Account.objects.filter(id=account.id).update(expenses=F('expenses') + new_value)
                
                # Update Project - add to existing gasto value
                Project.objects.filter(id=project_id).update(gasto=F('gasto') + new_value)
                
                # Update MonthlyFinancialSummary
                if createdm:
                    # For new monthly summaries, set the initial value directly
                    MonthlyFinancialSummary.objects.filter(id=monthly_summary.id).update(total_expenses=new_value)
                else:
                    # For existing summaries, add to current value
                    MonthlyFinancialSummary.objects.filter(id=monthly_summary.id).update(total_expenses=F('total_expenses') + new_value)
                
                define_type_for_summary(monthly_summary, project.type, -new_value, createdm)
                if new_value < 0:
                    acc_mov_description = f"Se redujo el gasto en ${abs(new_value)}"
                else:
                    acc_mov_description = f"Se ingreso el gasto de ${new_value}"  
                    
                # Refresh to see actual values after update
                monthly_summary.refresh_from_db()
                print(f"Monthly expenses after update: {monthly_summary.total_expenses}") 
                
            elif field == 'est':
                # Update Account
                Account.objects.filter(id=account.id).update(estimated=new_value)
                
                # Update Project - set the price value directly (not additive for estimates)
                Project.objects.filter(id=project_id).update(price=new_value)
                
                acc_mov_description = f"Se ingreso costo final de ${new_value}"
            else:
                print(f"Error: Invalid field type '{field}'")
                return None
            
            # Update networth for both account and monthly summary
            if created:
                # For new accounts, calculate networth from current values
                account.refresh_from_db()  # Get the updated values
                Account.objects.filter(id=account.id).update(
                    netWorth=F('advance') - F('expenses')
                )
            else:
                # For existing accounts, just update networth
                Account.objects.filter(id=account.id).update(
                    netWorth=F('advance') - F('expenses')
                )
            
            # Always update monthly summary networth after updating totals
            MonthlyFinancialSummary.objects.filter(id=monthly_summary.id).update(
                total_networth=F('total_advance') - F('total_expenses')
            )

            # Create movement record
            # Use custom description if provided, otherwise use auto-generated one
            final_description = custom_description if custom_description else acc_mov_description
            movement = AccountMovement.objects.create(
                account=account,
                project=project,
                amount=new_value,
                movement_type='ADV' if field == 'adv' else 'EXP' if field == 'exp' else 'EST',
                description=final_description
            )
            print(f"Created movement record: {movement}")
            
            # Refresh objects to get updated values for logging
            account.refresh_from_db()
            monthly_summary.refresh_from_db()
            print(f"Account netWorth after update: {account.netWorth}")
            print(f"Monthly summary netWorth after update: {monthly_summary.total_networth}")
            
            return account
            
    except Project.DoesNotExist:
        print(f"Error: Project with id {project_id} does not exist")
        return None
    except Exception as e:
        print(f"Error in create_acc_entry: {e}")
        import traceback
        traceback.print_exc()
        return None

def accounting_mov_display(request: HttpRequest, 
                           pk: Optional[int] = None
                           ) -> HttpResponse:
    """
    Display the accounting information for all projects or for a specific project.
    Optimized version with proper pagination and query optimization.
    Filters by user (staff sees all, regular users see only their data).
    """
    logger.info(f"Loading accounting movements for project: {pk}")
    
    # Optimized base query with select_related for foreign keys
    accounts_query = AccountMovement.objects.select_related(
        'project', 
        'project__client',
        'account'
    ).exclude(movement_type='EST')
    
    # Filtrar por usuario: staff ve todo, usuarios normales solo lo suyo
    if not request.user.is_staff:
        accounts_query = accounts_query.filter(project__created_by=request.user)
    
    # If project pk is provided in URL, filter by it
    if pk is not None:
        accounts_query = accounts_query.filter(project__id=pk)
    
    # Apply date filtering if requested
    if request.GET.get('filter') == 'true':
        start_date = request.GET.get('start-date')
        end_date = request.GET.get('end-date')
        
        try:
            # Apply start date filter if provided
            if start_date:
                accounts_query = accounts_query.filter(created_at__gte=start_date)
            
            # Apply end date filter if provided
            if end_date:
                # Add 1 day to include the entire end date
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                end_date_next = (end_date_obj + timedelta(days=1)).strftime('%Y-%m-%d')
                accounts_query = accounts_query.filter(created_at__lt=end_date_next)
        except ValueError:
            # Handle invalid date format gracefully
            pass
    
    # Order by date (newest first) and limit results for better performance
    accounts_query = accounts_query.order_by('-created_at')
    
    # Add pagination to avoid loading too many records at once
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    paginator = Paginator(accounts_query, 50)  # Show 50 movements per page
    page = request.GET.get('page', 1)
    
    try:
        accounts_mov = paginator.page(page)
    except PageNotAnInteger:
        accounts_mov = paginator.page(1)
    except EmptyPage:
        accounts_mov = paginator.page(paginator.num_pages)
    
    # Get count efficiently
    total_movements = accounts_query.count()
    
    logger.info(f"Loaded {accounts_mov.object_list.count()} movements (page {page} of {paginator.num_pages})")
    
    context = {
        'accounts_mov': accounts_mov,
        'start_date': request.GET.get('start-date', ''),
        'end_date': request.GET.get('end-date', ''),
        'project_id': pk,
        'total_movements': total_movements,
        'page_obj': accounts_mov,  # For pagination template
    }
    
    return render(request, 'accounting_template.html', context)

def define_type_for_summary(summary: MonthlyFinancialSummary, 
                            project_type: str, 
                            amount: Decimal,
                            is_new_summary: bool = False
                            ) -> None:
    """
    Helper function to define the project type and update the summary using F() expressions.
    This ensures atomic database updates and prevents race conditions.
    
    Args:
        summary: The monthly summary object
        project_type: The type of project
        amount: The amount to add/subtract
        is_new_summary: Whether this is a newly created summary (use direct assignment vs F() addition)
    """
    summary_id = summary.id
    
    if project_type == 'Mensura':
        if is_new_summary:
            MonthlyFinancialSummary.objects.filter(id=summary_id).update(total_net_mensura=amount)
        else:
            MonthlyFinancialSummary.objects.filter(id=summary_id).update(
                total_net_mensura=F('total_net_mensura') + amount
            )
      
    elif project_type == 'Estado Parcelario':
        if is_new_summary:
            MonthlyFinancialSummary.objects.filter(id=summary_id).update(total_net_est_parc=amount)
        else:
            MonthlyFinancialSummary.objects.filter(id=summary_id).update(
                total_net_est_parc=F('total_net_est_parc') + amount
            )
    elif project_type == 'Amojonamiento':
        if is_new_summary:
            MonthlyFinancialSummary.objects.filter(id=summary_id).update(total_net_amoj=amount)
        else:
            MonthlyFinancialSummary.objects.filter(id=summary_id).update(
                total_net_amoj=F('total_net_amoj') + amount
            )
    elif project_type == 'Relevamiento':
        if is_new_summary:
            MonthlyFinancialSummary.objects.filter(id=summary_id).update(total_net_relev=amount)
        else:
            MonthlyFinancialSummary.objects.filter(id=summary_id).update(
                total_net_relev=F('total_net_relev') + amount
            )
    elif project_type == 'Legajo Parcelario':
        if is_new_summary:
            MonthlyFinancialSummary.objects.filter(id=summary_id).update(total_net_leg=amount)
        else:
            MonthlyFinancialSummary.objects.filter(id=summary_id).update(
                total_net_leg=F('total_net_leg') + amount
            )
    else:
        logger.error(f"Unknown project type: {project_type}. Cannot update summary.")


@login_required
def create_manual_acc_entry (request, pk): 
    """ 
    User can create a manual account entry for a project.
    This function modifies the project data directly and creates account movements.
    
    Uses transaction.atomic to ensure data consistency across:
    - Project field updates (price, adv, gasto)
    - Account creation/updates
    - Monthly summary updates
    - Movement record creation
    """
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                project = get_object_or_404(Project, id=pk)
                form = ManualAccountEntryForm(request.POST)
                
                if form.is_valid():
                    # Determine movement type
                    movement_type = form.cleaned_data['movement_type']
                    amount = form.cleaned_data['amount']
                    description = form.cleaned_data.get('description', '')
                    
                    # Store old values for accounting
                    old_price = project.price or Decimal('0.00')
                    old_adv = project.adv or Decimal('0.00')
                    old_gasto = project.gasto or Decimal('0.00')
                    
                    # Update project fields directly based on movement type
                    if movement_type == 'ADV':
                        project.adv = (project.adv or Decimal('0.00')) + amount
                        logger.info(f"Anticipo agregado: ${amount} al proyecto {pk}")
                        
                        # Create accounting entry
                        create_acc_entry(
                            project_id=project.id,
                            field='adv',
                            old_value=old_adv,
                            new_value=amount,
                            custom_description=description
                        )
                        
                    elif movement_type == 'EXP':
                        project.gasto = (project.gasto or Decimal('0.00')) + amount
                        logger.info(f"Gasto agregado: ${amount} al proyecto {pk}")
                        
                        # Create accounting entry
                        create_acc_entry(
                            project_id=project.id,
                            field='exp',
                            old_value=old_gasto,
                            new_value=amount,
                            custom_description=description
                        )
                        
                    elif movement_type == 'EST':
                        project.price = amount  # For estimates, we set the total price
                        logger.info(f"Presupuesto establecido: ${amount} para proyecto {pk}")
                        
                        # Create accounting entry
                        create_acc_entry(
                            project_id=project.id,
                            field='est',
                            old_value=old_price,
                            new_value=amount,
                            custom_description=description
                        )
                    
                    # Save the project with updated values
                    project.save()
                    
                    # The AccountMovement is already created by create_acc_entry()
                    # No need to create it manually here
                    
                    # Determine redirect based on entry type
                    if movement_type == 'EST':
                        return redirect('projectview', pk=project.id)
                    else:
                        return redirect('accounting_display', pk=project.id)
                        
                else:
                    logger.warning(f"Formulario inválido para proyecto {pk}: {form.errors}")
                    
        except Exception as e:
            logger.error(f"Error en entrada manual proyecto {pk}: {str(e)}")
            # Add error message to form
            if 'form' in locals():
                form.add_error(None, f"Error procesando la entrada: {str(e)}")
            else:
                form = ManualAccountEntryForm()
                form.add_error(None, f"Error procesando la entrada: {str(e)}")
            
    else:
        # Render the form for GET requests
        form = ManualAccountEntryForm()
    
    # Get project for template context
    try:
        project = get_object_or_404(Project, id=pk)
        return render(request, 'account_form.html', {'form': form, 'project': project})
    except Exception as e:
        logger.error(f"Error obteniendo proyecto {pk}: {str(e)}")
        return render(request, 'account_form.html', {'form': form})


def get_earnings_per_client(count: int = 10, user=None):
    """
    This view returns the earnings per client separated by flag status.
    Shows top earnings for both flag=True (VIP clients) and flag=False (regular clients).
    Ordered by net earnings (advance - expenses).
    Filters by user if provided (staff sees all, regular users see only their data).
    """
    logger.info(f"Getting top {count} earnings for both VIP and regular clients")
    
    def get_clients_earnings_by_flag(flag_value: bool, limit: int):
        """Helper function to get earnings data for clients by flag status"""
        clients_earnings = []
        
        # Query desde Account hacia Client a través de Project, filtrado por flag y usuario
        base_query = Account.objects.select_related('project__client').filter(
            project__client__flag=flag_value
        )
        
        # Filtrar por usuario si no es staff
        if user and not user.is_staff:
            base_query = base_query.filter(project__created_by=user)
        
        clients_data = base_query.values(
            'project__client__id',
            'project__client__name'
        ).annotate(
            net=Sum('netWorth'), # Calculate net earnings for ordering
            projects_count=Count('project', distinct=True)
        ).order_by('-net')[:limit]  # Order by net earnings (highest first)

        for client_data in clients_data:

            net_earnings = client_data['net'] or Decimal('0.00')

            # Obtener el objeto Client para usar los métodos que creamos
            client = Client.objects.get(id=client_data['project__client__id'])
            
            clients_earnings.append({
                'client': client,
                'net_earnings': format_currency(net_earnings),
                'projects_count': client_data['projects_count'],
                'active_projects': client.active_projects_count,
                'earnings_by_type': client.earnings_by_project_type,
                'projects_by_type': dict(client.projects_count_by_type.values_list('type', 'count')),
                
            })
            
        return clients_earnings
    
    # Obtener top earnings para clientes VIP (flag=True)
    fix_clients_earnings = get_clients_earnings_by_flag(flag_value=True, limit=count)
    
    # Obtener top earnings para clientes regulares (flag=False)  
    regular_clients_earnings = get_clients_earnings_by_flag(flag_value=False, limit=count)
    
    context = {
        'fix_clients_earnings': fix_clients_earnings,
        'regular_clients_earnings': regular_clients_earnings,
        'count': count,
        'project_types': ['Estado Parcelario', 'Mensura', 'Amojonamiento', 'Relevamiento', 'Legajo Parcelario']
    }

    return context

@login_required
def display_earnings(request, count: int = 10):
    """
    Display earnings for all clients
    Filters by user (staff sees all, regular users see only their data)
    """
    context = get_earnings_per_client(count=count, user=request.user)
    context['count'] = count  # Add count to context for template
    return render(request, 'earnings_per_client.html', context)

@login_required  
def client_detailed_earnings(request, client_id: int):
    """
    Detailed earnings view for a specific client.
    Shows all projects with their individual earnings.
    Filters by user (staff sees all, regular users see only their data).
    """
    client = get_object_or_404(Client, id=client_id)
    
    # Get all projects with their accounts for this client - filtrar por usuario
    if request.user.is_staff:
        projects = Project.objects.filter(client=client)
    else:
        projects = Project.objects.filter(client=client, created_by=request.user)
    
    accounts = Account.objects.filter(project__in=projects)

    for project in projects:
        try:
            account = project.account
            net_earnings = (account.advance or Decimal('0.00')) - (account.expenses or Decimal('0.00'))
            projects_data.append({
                'project': project,
                'account': accounts.get(project=project),
                'net_earnings': net_earnings,
                'status': 'Cerrado' if project.closed else 'Pausado' if project.paused else 'Activo'
            })
        except:
            # Project without account
            projects_data.append({
                'project': project,
                'account': None,
                'net_earnings': Decimal('0.00'),
                'status': 'Sin cuenta'
            })
    
    context = {
        'client': client,
        'projects_data': projects_data,
        'total_net_earnings': client.total_net_earnings,
        'earnings_by_type': client.earnings_by_project_type,
        'projects_by_type': client.projects_count_by_type,
        'total_projects': client.total_projects_count,
        'active_projects': client.active_projects_count
    }
    
    return render(request, 'client_detailed_earnings.html', context)
    