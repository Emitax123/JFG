from django.shortcuts import render
from .models import Account, AccountMovement, MonthlyFinancialSummary
from ProjectManager.models import Project
from django.db import transaction
from datetime import datetime, timedelta, timezone
# Create your views here.

def create_account(project_id):
    """
    Create an account for a project if it does not already exist.
    """
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

def create_acc_entry(project_id, field, old_value, new_value):
    """
    Create an account entry for a project when a field is updated.
    """
    try:
        with transaction.atomic():
            project = Project.objects.get(id=project_id)
            if Account.objects.filter(project=project).exists():
                account = Account.objects.get(project=project)
            else:
                account = Account(project=project)

            account, created = Account.objects.get_or_create(project=project)
            monthly_summary, createdm = MonthlyFinancialSummary.objects.get_or_create(
                year=int(timezone.now().year),
                month=int(timezone.now().month)
            )
            if field == 'adv':

                account.advance = old_value + new_value
                monthly_summary.total_advance += new_value
                if new_value < 0:
                    acc_mov_description=f"Se devolvieron ${abs(new_value)}"
                else:
                    acc_mov_description=f"Se cobraron ${new_value}"
            elif field == 'exp':
                account.expenses = old_value + new_value
                monthly_summary.total_expenses += new_value
                if new_value < 0:
                    acc_mov_description=f"Se redujo el gasto en ${abs(new_value)}"
                else:
                    acc_mov_description=f"Se ingreso el gasto de ${new_value}"
            elif field == 'est':
                account.estimated = new_value
                monthly_summary.total_estimated += new_value
                acc_mov_description=f"Se ingreso costo final de ${new_value}"
            
            account.netWorth = account.advance - account.expenses
            account.save()
            monthly_summary.total_networth = monthly_summary.total_advance - monthly_summary.total_expenses
            monthly_summary.save()
            #Create Record
            AccountMovement.objects.create(
                account=account,
                project=project,
                amount=new_value,
                movement_type='ADV' if field == 'adv' else 'EXP' if field == 'exp' else 'EST',
                description=acc_mov_description
            )
            return account
    except Project.DoesNotExist:
        return None

def accounting_mov_display(request, pk=None):

    """
    Display the accounting information for all projects or for a specific project.
    """
    # Create base query that selects all movements except 'EST' type with prefetched related data
    accounts_query = AccountMovement.objects.select_related('project', 'project__client').exclude(movement_type='EST')
    
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
            # Just continue without applying the filter
            pass
    
    # Get the final queryset ordered by date (newest first)
    accounts_mov = accounts_query.order_by('-created_at')
    
    
    # Pass the filter parameters to the template context to maintain state
    context = {
        'accounts_mov': accounts_mov,
        'start_date': request.GET.get('start-date', ''),
        'end_date': request.GET.get('end-date', ''),
        'project_id': pk  # Pass the project ID to the template
    }
    
    return render(request, 'accounting_template.html', context)

def copy_projects_to_accounting(request):
    """
    Copy all projects to the accounting system.
    """
    projects = Project.objects.all()
    for project in projects:
        account = create_account(project.id)
        account.estimated = project.price
        account.advance = project.adv
        account.expenses = project.gasto
        account.netWorth = project.adv - project.gasto
        account.created = project.created
        account.save()
    return render(request, 'good.html', {'message': 'All projects copied to accounting.'})

