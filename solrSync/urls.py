from django.conf.urls import url
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    url(r'^resourcelist.xml/$', views.resourcelist, name="resourcelist"),
    url(r'^changelist.xml/$', views.changelist, name="changelist"),
    url(r'^resourcesync/$', views.resourceSync, name="resourceSync"),
    url(r'^stream/$', views.stream_response, name="stream_response"),
]
