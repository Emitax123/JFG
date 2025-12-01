# views_group_projects.py
# Vistas para proyectos grupales/colaborativos

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.db.models import Q, Sum
from decimal import Decimal
from .models import Project, ProjectCollaborator
from Accounting.models import Account
import logging

logger = logging.getLogger(__name__)


@login_required
def group_projects_list(request: HttpRequest) -> HttpResponse:
    """
    Vista para listar todos los proyectos grupales donde el usuario participa.
    """
    view_mode = request.GET.get('view', 'cards')
    # Obtener IDs de proyectos donde el usuario es colaborador
    collaborated_project_ids = ProjectCollaborator.objects.filter(
        user=request.user
    ).values_list('project_id', flat=True)
    
    # Proyectos grupales donde el usuario es colaborador o creador
    projects = Project.objects.filter(
        Q(id__in=collaborated_project_ids) | Q(created_by=request.user),
        is_group_project=True
    ).select_related('client').order_by('-created').distinct()
    
    # Verificar si no hay proyectos
    no_projects = not projects.exists()
    
    context = {
        'projects': projects,
        'no_projects': no_projects,
        'view_mode': view_mode,
    }
    
    return render(request, 'project_list_template.html', context)


@login_required
def group_project_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Vista detallada de un proyecto grupal con información de colaboradores.
    """
    project = get_object_or_404(Project, pk=pk, is_group_project=True)
    
    # Verificar que el usuario tenga acceso (creador o colaborador)
    is_creator = project.created_by == request.user
    is_collaborator = ProjectCollaborator.objects.filter(
        project=project, user=request.user
    ).exists()
    
    if not (is_creator or is_collaborator or request.user.is_staff):
        return render(request, 'error.html', {
            'message': 'No tienes permiso para ver este proyecto grupal.'
        })
    
    # Obtener colaboradores
    collaborators = ProjectCollaborator.objects.filter(
        project=project
    ).select_related('user').order_by('-percentage')
    
    # Calcular porcentaje total asignado
    total_percentage = collaborators.aggregate(
        total=Sum('percentage')
    )['total'] or Decimal('0.00')
    
    # Obtener datos financieros
    try:
        account = project.account
        net_earnings = (account.advance or Decimal('0.00')) - (account.expenses or Decimal('0.00'))
        
        # Calcular ganancias por colaborador
        collaborators_earnings = []
        for collab in collaborators:
            user_earnings = (net_earnings * collab.percentage) / Decimal('100.00')
            collaborators_earnings.append({
                'user': collab.user,
                'percentage': collab.percentage,
                'earnings': user_earnings
            })
    except Account.DoesNotExist:
        account = None
        net_earnings = Decimal('0.00')
        collaborators_earnings = []
    
    context = {
        'project': project,
        'is_creator': is_creator,
        'is_collaborator': is_collaborator,
        'collaborators': collaborators,
        'collaborators_earnings': collaborators_earnings,
        'total_percentage': total_percentage,
        'account': account,
        'net_earnings': net_earnings,
        'status': 'Cerrado' if project.closed else 'Pausado' if project.paused else 'Activo'
    }
    
    return render(request, 'group_project_detail.html', context)


@login_required
def manage_collaborators(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Vista para gestionar colaboradores de un proyecto grupal.
    Solo el creador puede gestionar colaboradores.
    """
    project = get_object_or_404(Project, pk=pk, is_group_project=True)
    
    # Solo el creador puede gestionar colaboradores
    if project.created_by != request.user and not request.user.is_staff:
        return render(request, 'error.html', {
            'message': 'Solo el creador del proyecto puede gestionar colaboradores.'
        })
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            user_id = request.POST.get('user_id')
            percentage = request.POST.get('percentage')
            
            try:
                user = User.objects.get(id=user_id)
                percentage_decimal = Decimal(percentage)
                
                # Verificar que no exceda 100%
                total_current = ProjectCollaborator.objects.filter(
                    project=project
                ).aggregate(total=Sum('percentage'))['total'] or Decimal('0.00')
                
                if total_current + percentage_decimal > Decimal('100.00'):
                    return JsonResponse({
                        'success': False,
                        'message': f'No se puede agregar. Total actual: {total_current}%. '
                                 f'Intentando agregar: {percentage_decimal}%.'
                    })
                
                # Crear o actualizar colaborador
                collab, created = ProjectCollaborator.objects.update_or_create(
                    project=project,
                    user=user,
                    defaults={'percentage': percentage_decimal}
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Colaborador agregado exitosamente.'
                })
                
            except Exception as e:
                logger.error(f"Error adding collaborator: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'message': f'Error: {str(e)}'
                })
        
        elif action == 'remove':
            collab_id = request.POST.get('collab_id')
            try:
                collab = ProjectCollaborator.objects.get(id=collab_id, project=project)
                collab.delete()
                return JsonResponse({
                    'success': True,
                    'message': 'Colaborador eliminado exitosamente.'
                })
            except Exception as e:
                logger.error(f"Error removing collaborator: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'message': f'Error: {str(e)}'
                })
        
        elif action == 'update':
            collab_id = request.POST.get('collab_id')
            new_percentage = request.POST.get('percentage')
            
            try:
                collab = ProjectCollaborator.objects.get(id=collab_id, project=project)
                new_percentage_decimal = Decimal(new_percentage)
                
                # Verificar que no exceda 100%
                total_current = ProjectCollaborator.objects.filter(
                    project=project
                ).exclude(id=collab_id).aggregate(
                    total=Sum('percentage')
                )['total'] or Decimal('0.00')
                
                if total_current + new_percentage_decimal > Decimal('100.00'):
                    return JsonResponse({
                        'success': False,
                        'message': f'No se puede actualizar. Total de otros: {total_current}%.'
                    })
                
                collab.percentage = new_percentage_decimal
                collab.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Porcentaje actualizado exitosamente.'
                })
                
            except Exception as e:
                logger.error(f"Error updating collaborator: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'message': f'Error: {str(e)}'
                })
    
    # GET request - mostrar formulario
    collaborators = ProjectCollaborator.objects.filter(
        project=project
    ).select_related('user')
    
    # Usuarios disponibles para agregar (excluir solo los ya colaboradores, incluir al creador)
    existing_user_ids = collaborators.values_list('user_id', flat=True)
    available_users = User.objects.exclude(id__in=existing_user_ids)
    
    total_percentage = collaborators.aggregate(
        total=Sum('percentage')
    )['total'] or Decimal('0.00')
    
    remaining_percentage = Decimal('100.00') - total_percentage
    
    context = {
        'project': project,
        'collaborators': collaborators,
        'available_users': available_users,
        'total_percentage': total_percentage,
        'remaining_percentage': remaining_percentage,
        'current_user_id': request.user.id
    }
    
    return render(request, 'manage_collaborators.html', context)


@login_required
def toggle_group_project(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Convierte un proyecto normal en grupal o viceversa.
    Solo el creador puede hacer esto.
    """
    project = get_object_or_404(Project, pk=pk)
    
    if project.created_by != request.user and not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'message': 'Solo el creador puede cambiar el tipo de proyecto.'
        })
    
    try:
        with transaction.atomic():
            project.is_group_project = not project.is_group_project
            project.save()
            
            if not project.is_group_project:
                # Si se convierte a normal, eliminar todos los colaboradores
                ProjectCollaborator.objects.filter(project=project).delete()
            
            return JsonResponse({
                'success': True,
                'is_group_project': project.is_group_project,
                'message': f'Proyecto convertido a {"grupal" if project.is_group_project else "individual"}.'
            })
    except Exception as e:
        logger.error(f"Error toggling group project: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })
