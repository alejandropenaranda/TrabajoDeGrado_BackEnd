"""
URL configuration for TrabajoDeGrado_BackEnd project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('core/login', views.user_login),
    path('core/register', views.user_register),
    path('core/profile', views.user_profile),

    #Esta es la url que muestra la data de los docentes para las tablas 
    path('core/average_grades', views.get_average_grades),

    #Esta url es para fortalezas y debilidades cuantitativas
    path('core/cuant_fort_deb', views.get_cuant_fort_deb),

    # Esta url es para identificar las fortalezas y debilidades cualitativas de un docente
    path('core/cual_fort_deb', views.get_cual_fort_deb),

    # Esta url es para identificar las fortalezas y debilidades cualitativas de un docente
    path('core/cual_analysis', views.find_strengths_weaknesses),
    # Esta url es para identificar las fortalezas y debilidades cualitativas de todos los docente
    path('core/cual_analysis_all', views.find_strengths_weaknesses_all_teachers),

    #Esta url es para peor y mejor comentario
    path('core/mejor_peor_comentario', views.get_best_and_worst_comment),

    # Estos son las urls para los graficos de barras
    path('core/prom_fac_escuela', views.get_average_grades_school_and_overall),
    path('core/cual_prom', views.get_qualitative_average_grades),
    path('core/cuant_prom', views.get_cuantitative_average_grades),

    path('core/analizar_comentarios', views.get_wordcloud_and_frequent_words),
]
