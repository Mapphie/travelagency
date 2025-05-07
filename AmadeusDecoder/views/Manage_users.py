'''
Created on 8 Sep 2022

'''
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import datetime, timezone
from AmadeusDecoder.models.invoice.Ticket import Ticket

from AmadeusDecoder.models.user.Users import User
from AmadeusDecoder.models.user.Users import Role
from AmadeusDecoder.forms import UserForm

def paginate_queryset(request, queryset, per_page=25):
    """Helper function to paginate any queryset."""
    row_num = request.GET.get('paginate_by', per_page)
    page_num = request.GET.get('page', 1)
    
    try:
        row_num = int(row_num)
    except (ValueError, TypeError):
        row_num = per_page
        
    paginator = Paginator(queryset, row_num)
    
    try:
        page_obj = paginator.page(page_num)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
        
    return page_obj, row_num

def verify_user_password(request, user_id, password):
    """Verify user password and return authentication status with message."""
    try:
        user = User.objects.get(pk=user_id)
        user_auth = authenticate(request, username=user.email, password=password)
        
        if user_auth is not None:
            return True, ""
        return False, "Mot de passe incorrect"
    except User.DoesNotExist:
        return False, "Utilisateur non trouvé"

@login_required(login_url='index')
def users(request):
    """Display all users with pagination."""
    users_list = User.objects.all().select_related('role')
    page_obj, row_num = paginate_queryset(request, users_list)
    
    context = {
        'users': users_list,
        'roles': Role.objects.all(),
        'page_obj': page_obj,
        'row_num': row_num
    }
    return render(request, 'manage_users.html', context)

@login_required(login_url='index')
def register(request):
    """Register a new user."""
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Utilisateur créé avec succès")
            return redirect('users')
    else:
        form = UserForm()
    
    context = {
        'form': form,
        'users': User.objects.all()
    }
    return render(request, 'add-user.html', context)

@login_required(login_url='index')
def user_details(request, user_id):
    """Display user details."""
    user = get_object_or_404(User, pk=user_id)
    
    context = {
        'user': user,
        'roles': Role.objects.all()
    }
    return render(request, 'user-details.html', context)

def _toggle_user_status(request, activate=True):
    """Helper function to activate or deactivate a user."""
    if request.method != 'POST':
        return JsonResponse({'status': 405, 'message': 'Méthode non autorisée'})
    
    user_id = request.POST.get('user')
    connected_user_id = request.POST.get('connected_user')
    password = request.POST.get('password')
    
    is_authenticated, error_message = verify_user_password(request, connected_user_id, password)
    
    if not is_authenticated:
        return JsonResponse({'status': 10, 'message': error_message})
    
    try:
        user = User.objects.get(pk=user_id)
        
        if user.is_active == activate:
            status_text = "activé" if activate else "archivé"
            return JsonResponse({'status': 20, 'message': f"Utilisateur déjà {status_text}"})
        
        user.is_active = activate
        user.save(update_fields=['is_active'])
        
        status_text = "réactivé" if activate else "archivé"
        return JsonResponse({'status': 200, 'message': f"Utilisateur {status_text} avec succès"})
    
    except User.DoesNotExist:
        return JsonResponse({'status': 404, 'message': "Utilisateur non trouvé"})

@login_required(login_url='index')
def archive_user(request):
    """Archive a user (set is_active to False)."""
    return _toggle_user_status(request, activate=False)

@login_required(login_url='index')
def reactive_user(request):
    """Reactivate a user (set is_active to True)."""
    return _toggle_user_status(request, activate=True)

@login_required(login_url='index')
def update_password(request):
    """Update user password."""
    if request.method != 'POST':
        return JsonResponse({'status': 405, 'message': 'Méthode non autorisée'})
    
    current_password = request.POST.get('currentPassword')
    new_password = request.POST.get('newPassword')
    user_id = request.POST.get('user_id')
    
    try:
        user = User.objects.get(pk=user_id)
        user_authenticated = authenticate(request, username=user.email, password=current_password)
        
        if user_authenticated is not None:
            user.set_password(new_password)
            user.save(update_fields=['password'])
            return JsonResponse({'status': 200, 'message': "Mot de passe modifié"})
        else:
            return JsonResponse({'status': 10, 'message': "Mot de passe actuel incorrect"})
    
    except User.DoesNotExist:
        return JsonResponse({'status': 404, 'message': "Utilisateur non trouvé"})

@login_required(login_url='index')
def update_info(request):
    """Update user information."""
    if request.method != 'POST':
        return JsonResponse({'status': 405, 'message': 'Méthode non autorisée'})
    
    user_id = request.POST.get('user')
    connected_user_id = request.POST.get('connected_user')
    password = request.POST.get('password')
    
    is_authenticated, error_message = verify_user_password(request, connected_user_id, password)
    
    if not is_authenticated:
        return JsonResponse({'status': 10, 'message': error_message})
    
    try:
        user = User.objects.get(pk=user_id)
        role_id = request.POST.get('role')
        
        try:
            role = Role.objects.get(pk=role_id)
        except Role.DoesNotExist:
            return JsonResponse({'status': 404, 'message': "Rôle non trouvé"})
        
        user.name = request.POST.get('name')
        user.first_name = request.POST.get('first_name')
        user.email = request.POST.get('email')
        user.role = role
        user.save(update_fields=['name', 'first_name', 'email', 'role'])
        
        return JsonResponse({'status': 200, 'message': "Informations modifiées"})
    
    except User.DoesNotExist:
        return JsonResponse({'status': 404, 'message': "Utilisateur non trouvé"})

@login_required(login_url="index")
def user_research(request):
    """Search for users by name, first name, email, or username."""
    if request.method != 'POST' or not request.POST.get('user_research'):
        return JsonResponse({'results': [], 'pnr_count': 0})
    
    search_term = request.POST.get('user_research')
    
    # Utilisation de Q objects pour des recherches complexes
    users = User.objects.filter(
        Q(name__icontains=search_term) | 
        Q(first_name__icontains=search_term) | 
        Q(email__icontains=search_term) | 
        Q(username__icontains=search_term)
    ).select_related('role')
    
    results = [
        {
            'id': user.id,
            'name': user.name,
            'first_name': user.first_name,
            'username': user.username,
            'email': user.email,
            'role': user.role.name
        }
        for user in users
    ]
    
    return JsonResponse({'results': results, 'pnr_count': len(results)})

@login_required(login_url="index")
def user_filter(request):
    """Filter users by role."""
    if request.method != 'POST' or not request.POST.get('role_id'):
        return JsonResponse({'results': [], 'pnr_count': 0})
    
    role_id = request.POST.get('role_id')
    
    users = User.objects.filter(role_id=role_id).select_related('role')
    
    results = [
        {
            'id': user.id,
            'name': user.name,
            'first_name': user.first_name,
            'username': user.username,
            'email': user.email,
            'role': user.role.name
        }
        for user in users
    ]
    
    return JsonResponse({'results': results, 'pnr_count': len(results)})