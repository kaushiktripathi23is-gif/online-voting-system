# voting_app/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Main Pages
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('verify/', views.verify_user, name='verify'),
    
    # --- THIS IS THE NEW LINE YOU ASKED FOR ---
    path('results/', views.consolidated_results_view, name='consolidated_results'),
    # --- END OF NEW LINE ---

    # Voting Process
    path('elections/', views.election_list, name='election_list'),
    path('elections/<int:election_id>/', views.vote_page, name='vote_page'),
    path('elections/<int:election_id>/results/', views.results_view, name='results'),
    path('vote/<int:vote_id>/slip/', views.download_slip, name='download_slip'),
    
    # AJAX Endpoints (for JavaScript)
    path('ajax/register-face/', views.ajax_register_face, name='ajax_register_face'),
    path('ajax/check-face-and-vote/', views.ajax_check_face_and_vote, name='ajax_check_face_and_vote'),
]
