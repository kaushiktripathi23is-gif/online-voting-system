# voting_app/admin.py

from django.contrib import admin, messages
from .models import Election, Candidate, VoterProfile, Vote

@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    """
    Customizes the Admin view for Elections.
    """
    list_display = (
        'title', 
        'start_date', 
        'end_date', 
        'is_active', 
        'results_declared'  # <-- The field from last time
    )
    list_filter = ('is_active', 'results_declared')
    search_fields = ('title',)
    
    # --- THIS IS THE NEW SECTION ---
    
    # Add our new custom action to the dropdown
    actions = ['declare_results_and_stop_election']

    def declare_results_and_stop_election(self, request, queryset):
        """
        This is the new action. It will run on all selected elections.
        """
        # We update all selected elections in one go
        rows_updated = queryset.update(results_declared=True, is_active=False)
        
        # Send a success message back to the admin
        if rows_updated == 1:
            message_bit = "1 election was"
        else:
            message_bit = f"{rows_updated} elections were"
        self.message_user(request, f"{message_bit} successfully stopped and results declared.", messages.SUCCESS)

    # This sets the name you see in the dropdown menu
    declare_results_and_stop_election.short_description = "Declare results and stop selected elections"
    # --- END OF NEW SECTION ---


@admin.register(VoterProfile)
class VoterProfileAdmin(admin.ModelAdmin):
    """
    Customizes the Admin view for VoterProfiles (our "Voters").
    """
    list_display = (
        'user', 
        'get_user_email',
        'college_id', 
        'is_verified'
    )
    list_filter = ('is_verified',)
    search_fields = ('user__username', 'user__email', 'college_id')

    @admin.display(description='Email')
    def get_user_email(self, obj):
        return obj.user.email


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    """
    Customizes the Admin view for Candidates.
    """
    list_display = ('name', 'election')
    list_filter = ('election',)
    search_fields = ('name', 'election__title')


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    """
    Customizes the Admin view for the Vote log.
    """
    list_display = ('voter', 'election', 'candidate', 'timestamp')
    list_filter = ('election', 'timestamp')
    search_fields = ('voter__username', 'election__title', 'candidate__name')
