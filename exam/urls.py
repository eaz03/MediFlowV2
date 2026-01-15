from django.urls import path
from exam import views as examViews

urlpatterns = [
    path('new-exam/', examViews.new_exam, name="new_exam"),
    path('bulk-insertion', examViews.bulk_insertion, name="bulk_insertion"),
    path('download/<int:path>', examViews.download, name="download"),
]
