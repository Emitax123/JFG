from decimal import Decimal
from django.shortcuts import render
from .models import Account, AccountMovement, MonthlyFinancialSummary
from ProjectManager.models import Project
from django.db import transaction
from datetime import datetime, timedelta
from django.utils import timezone
# Create your views here.

def create_account(project_id):
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

def create_acc_entry(project_id, field, old_value, new_value):
    """
    Create an account entry for a project when a field is updated.
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
            
            # Get or create the monthly summary
            current_year = int(timezone.now().year)
            current_month = int(timezone.now().month)
            
            monthly_summary, createdm = MonthlyFinancialSummary.objects.get_or_create(
                year=current_year,
                month=current_month
            )
            
            if createdm:
                print(f"Monthly summary created for {current_year}-{current_month}")
                # Initialize the monthly summary (returns the instance)
                summary_obj = MonthlyFinancialSummary.initialize(current_year, current_month)
                if summary_obj:
                    monthly_summary = summary_obj  # Use the returned instance
                    print(f"Successfully initialized monthly summary: {monthly_summary}")
            
            # Process based on field type
            if field == 'adv':
                account.advance = (account.advance or Decimal('0.00')) + new_value
                monthly_summary.total_advance = (monthly_summary.total_advance or Decimal('0.00')) + new_value
                define_type_for_summary(monthly_summary, project.type, new_value)
                if new_value < 0:
                    acc_mov_description = f"Se devolvieron ${abs(new_value)}"
                else:
                    acc_mov_description = f"Se cobraron ${new_value}"
            elif field == 'exp':
                account.expenses = (account.expenses or Decimal('0.00')) + new_value
                monthly_summary.total_expenses = (monthly_summary.total_expenses or Decimal('0.00')) + new_value
                define_type_for_summary(monthly_summary, project.type, -new_value)
                if new_value < 0:
                    acc_mov_description = f"Se redujo el gasto en ${abs(new_value)}"
                else:
                    acc_mov_description = f"Se ingreso el gasto de ${new_value}"   
            elif field == 'est':
                account.estimated = new_value           
                acc_mov_description = f"Se ingreso costo final de ${new_value}"
            else:
                print(f"Error: Invalid field type '{field}'")
                return None
            
            # Update net worth values
            account.netWorth = account.advance - account.expenses
            monthly_summary.total_networth = monthly_summary.total_advance - monthly_summary.total_expenses

            # Save both models
            print(f"Saving account with netWorth: {account.netWorth}")
            account.save()
            
            print(f"Saving monthly summary with netWorth: {monthly_summary.total_networth}")
            monthly_summary.save()
            
            # Create movement record
            movement = AccountMovement.objects.create(
                account=account,
                project=project,
                amount=new_value,
                movement_type='ADV' if field == 'adv' else 'EXP' if field == 'exp' else 'EST',
                description=acc_mov_description
            )
            print(f"Created movement record: {movement}")
            
            return account
            
    except Project.DoesNotExist:
        print(f"Error: Project with id {project_id} does not exist")
        return None
    except Exception as e:
        print(f"Error in create_acc_entry: {e}")
        import traceback
        traceback.print_exc()
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


def define_type_for_summary(summary, project_type, amount):
    """
    Helper function to define the project type and update the summary.
    """
    if project_type == 'Mensura':
        summary.total_net_mensura += amount
    elif project_type == 'Estado Parcelario':
        summary.total_net_est_parc += amount
    elif project_type == 'Amojonamiento':
        summary.total_net_amoj += amount
    elif project_type == 'Relevamiento':
        summary.total_net_relev += amount
    elif project_type == 'Legajo Parcelario':
        summary.total_net_leg += amount
    else:
        print(f"Unknown project type: {project_type}")
    return summary
