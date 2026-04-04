from django.urls import path
from buyer.views import login_page, logout_page, register_page, profile_page

urlpatterns = [
   path('login/' , login_page , name="login" ),
   path('register/' , register_page , name="register"),
   path('logout/', logout_page, name="logout"),
   path('profile/', profile_page, name="profile"),
]
