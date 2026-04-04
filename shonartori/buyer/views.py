from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Profile


def login_page(request):
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user_obj = User.objects.filter(username = email)

        if not user_obj.exists():
            messages.warning(request, 'Account not found.')
            return HttpResponseRedirect(request.path_info)


        if not user_obj[0].profile.is_email_verified:
            messages.warning(request, 'Your account is not verified.')
            return HttpResponseRedirect(request.path_info)

        user_obj = authenticate(username = email , password= password)
        if user_obj:
            login(request , user_obj)
            return redirect('/')

        

        messages.warning(request, 'Invalid credentials')
        return HttpResponseRedirect(request.path_info)


    return render(request ,'login.html')


def register_page(request):

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        user_obj = User.objects.filter(username = email)

        if user_obj.exists():
            messages.warning(request, 'Email is already taken.')
            return HttpResponseRedirect(request.path_info)

        print(email)

        user_obj = User.objects.create(first_name = first_name , last_name= last_name , email = email , username = email)
        user_obj.set_password(password)
        user_obj.save()

        messages.success(request, 'An email has been sent on your mail.')
        return HttpResponseRedirect(request.path_info)


    return render(request , 'register.html')


def logout_page(request):
    logout(request)
    return redirect('/')


@login_required(login_url="login")
def profile_page(request):
    user = request.user
    Profile.objects.get_or_create(user=user)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "update_profile":
            first_name = (request.POST.get("first_name") or "").strip()
            last_name = (request.POST.get("last_name") or "").strip()
            user.first_name = first_name
            user.last_name = last_name
            user.save(update_fields=["first_name", "last_name"])
            profile = user.profile
            if request.FILES.get("profile_image"):
                profile.profile_image = request.FILES["profile_image"]
                profile.save(update_fields=["profile_image"])
            messages.success(request, "Your profile was updated.")
            return redirect("profile")
        if action == "change_password":
            current = request.POST.get("current_password") or ""
            new_pw = request.POST.get("new_password") or ""
            confirm = request.POST.get("confirm_password") or ""
            if not user.check_password(current):
                messages.error(request, "Current password is incorrect.")
                return redirect("profile")
            if len(new_pw) < 8:
                messages.error(request, "New password must be at least 8 characters.")
                return redirect("profile")
            if new_pw != confirm:
                messages.error(request, "New passwords do not match.")
                return redirect("profile")
            user.set_password(new_pw)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password was updated.")
            return redirect("profile")
        messages.warning(request, "Invalid form submission.")
        return redirect("profile")
    return render(request, "profile.html", {"user": user})



# def activate_email(request , email_token):
#     try:
#         user = Profile.objects.get(email_token= email_token)
#         user.is_email_verified = True
#         user.save()
#         return redirect('/')
#     except Exception as e:
#         return HttpResponse('Invalid Email token')