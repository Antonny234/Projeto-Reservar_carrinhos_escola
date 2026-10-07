from django.contrib import admin
from django.urls import path, include
from reservas import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('reservas.urls')),

    
]

handler403 = 'reservas.views.handler403'
handler404 = 'reservas.views.handler404'
handler500 = 'reservas.views.handler500'
