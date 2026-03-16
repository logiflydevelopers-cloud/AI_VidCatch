from django.urls import path
from . import views

urlpatterns = [

    # create generation job
    path("create/", views.create_generation, name="create_generation"),

    # get generation status
    path("<str:job_id>/", views.get_generation, name="get_generation"),

    # list user generations
    path("my/", views.list_generations, name="my_generations"),
]