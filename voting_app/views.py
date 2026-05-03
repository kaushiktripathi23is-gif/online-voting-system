# voting_app/views.py

# --- ALL IMPORTS MUST BE AT THE TOP ---
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.db.models import Count
from django.utils import timezone
from django.urls import reverse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from .forms import CustomUserCreationForm, VoterProfileForm
from .models import VoterProfile, Election, Candidate, Vote

import cv2
import numpy as np
import base64
import json
from sklearn.neighbors import KNeighborsClassifier
# --- END OF IMPORTS ---


# --- Helper: Load Face Detector ---
face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')


# --- Standard Page Views ---

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def home(request):
    """
    Dashboard page. Checks verification status and directs user.
    """
    profile = request.user.voterprofile
    if not profile.is_verified:
        return redirect('verify')
        
    voted_elections_ids = Vote.objects.filter(voter=request.user).values_list('election_id', flat=True)
    
    return render(request, 'home.html', {
        'user': request.user,
        'voted_elections_ids': list(voted_elections_ids)
    })

@login_required
def verify_user(request):
    """
    Handles both GET and POST for the verification page.
    """
    profile = request.user.voterprofile
    if profile.is_verified:
        return redirect('home')

    if request.method == 'POST':
        form = VoterProfileForm(request.POST, instance=profile)
        if form.is_valid():
            college_id = form.cleaned_data['college_id']
            aadhaar = form.cleaned_data['aadhaar_number']
            
            error = False
            if VoterProfile.objects.filter(college_id=college_id).exclude(user=request.user).exists():
                form.add_error('college_id', 'This College ID is already registered.')
                error = True
            
            if VoterProfile.objects.filter(aadhaar_number=aadhaar).exclude(user=request.user).exists():
                form.add_error('aadhaar_number', 'This Aadhaar number is already registered.')
                error = True
            
            if not error:
                form.save()
    else:
        form = VoterProfileForm(instance=profile)

    return render(request, 'verify.html', {'form': form, 'profile': profile})

@login_required
def election_list(request):
    """
    Show all active elections.
    """
    now = timezone.now()
    elections = Election.objects.filter(is_active=True, start_date__lte=now, end_date__gte=now)
    
    voted_in = Vote.objects.filter(voter=request.user).values_list('election_id', flat=True)
    
    return render(request, 'election_list.html', {
        'elections': elections,
        'voted_in': list(voted_in)
    })

@login_required
def vote_page(request, election_id):
    """
    Display candidates for a specific election and the voting modal.
    """
    if not request.user.voterprofile.is_verified:
        return redirect('verify')

    try:
        election = Election.objects.get(id=election_id, is_active=True)
    except Election.DoesNotExist:
        return redirect('election_list')
        
    if Vote.objects.filter(voter=request.user, election=election).exists():
        return redirect('results', election_id=election_id)
        
    candidates = election.candidates.all()
    return render(request, 'vote_page.html', {
        'election': election,
        'candidates': candidates
    })

@login_required
def results_view(request, election_id):
    """
    Show results, but ONLY if the admin has declared them.
    """
    election = Election.objects.get(id=election_id)
    
    # --- THIS QUERY IS NOW AT THE TOP ---
    # Check if this user has voted in this election
    user_vote = Vote.objects.filter(voter=request.user, election=election).first()
    
    if not election.results_declared:
        # If results are not declared, show the pending page
        # --- `user_vote` IS NOW PASSED IN ---
        return render(request, 'results_pending.html', {
            'election': election,
            'user_vote': user_vote 
        })
        
    # This code will now only run if results_declared is True
    results = Candidate.objects.filter(election=election).annotate(
        vote_count=Count('vote')
    ).order_by('-vote_count')
    
    winner = results.first() 
    
    # user_vote is already calculated
    
    return render(request, 'results.html', {
        'election': election, 
        'results': results,
        'user_vote': user_vote,
        'winner': winner
    })


# --- AJAX Views (Handle JavaScript requests) ---
# Add this new function in views.py

@login_required
def consolidated_results_view(request):
    """
    Show a list of all declared elections and their winners.
    """
    # Get all elections that are marked as "results_declared"
    declared_elections = Election.objects.filter(results_declared=True).order_by('-end_date')

    results_data = []
    for election in declared_elections:
        # Find the winner for each election
        winner = Candidate.objects.filter(election=election).annotate(
            vote_count=Count('vote')
        ).order_by('-vote_count').first()

        results_data.append({'election': election, 'winner': winner})

    return render(request, 'consolidated_results.html', {
        'results_data': results_data
    })

@login_required
def ajax_register_face(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    try:
        data = json.loads(request.body)
        frames_b64 = data.get('frames', [])
        
        face_samples = []
        
        for frame_b64 in frames_b64:
            img_data = base64.b64decode(frame_b64)
            np_arr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            faces = face_detector.detectMultiScale(gray, 1.3, 5)
            
            if len(faces) != 1: continue
                
            for (x, y, w, h) in faces:
                face_roi = gray[y:y+h, x:x+w]
                resized_face = cv2.resize(face_roi, (50, 50))
                face_samples.append(resized_face)
        
        if len(face_samples) < 20:
            return JsonResponse({'success': False, 'error': 'Could not detect a clear face. Please try again in better lighting.'})

        face_data_array = np.array(face_samples)
        n_samples = face_data_array.shape[0]
        face_data_flat = face_data_array.reshape(n_samples, -1)

        face_data_serial = base64.b64encode(face_data_flat.tobytes()).decode('utf-8')
        shape = face_data_flat.shape
        dtype = str(face_data_flat.dtype)
        
        profile = request.user.voterprofile
        profile.face_data = json.dumps({
            'data': face_data_serial,
            'shape': shape,
            'dtype': dtype
        })
        profile.is_verified = True 
        profile.save()
        
        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def get_all_face_data():
    """
    Helper function to load all face data from the DB for the KNN model.
    """
    labels = []
    all_faces = []
    
    profiles = VoterProfile.objects.filter(is_verified=True, face_data__isnull=False)
    
    for profile in profiles:
        try:
            face_meta = json.loads(profile.face_data)
            data_serial = face_meta['data']
            shape = tuple(face_meta['shape'])
            dtype = np.dtype(face_meta['dtype'])
            
            data_bytes = base64.b64decode(data_serial)
            face_array = np.frombuffer(data_bytes, dtype=dtype).reshape(shape)
            
            for face in face_array:
                all_faces.append(face)
                labels.append(profile.user.id)
        except Exception as e:
            print(f"Error loading face data for user {profile.user.id}: {e}")
            continue
            
    return np.array(all_faces), np.array(labels)

@login_required
def ajax_check_face_and_vote(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    try:
        known_faces, known_labels = get_all_face_data()
        
        if len(known_labels) == 0:
            return JsonResponse({'success': False, 'error': 'No face data in system to compare against.'})

        knn = KNeighborsClassifier(n_neighbors=5)
        knn.fit(known_faces, known_labels)
        
        data = json.loads(request.body)
        frame_b64 = data.get('frame').split(',')[1]
        candidate_id = data.get('candidate_id')
        election_id = data.get('election_id')
        
        if not all([frame_b64, candidate_id, election_id]):
            return JsonResponse({'success': False, 'error': 'Missing data.'}, status=400)

        img_data = base64.b64decode(frame_b64)
        np_arr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        faces = face_detector.detectMultiScale(gray, 1.3, 5)
        
        if len(faces) != 1:
            return JsonResponse({'success': False, 'error': 'No clear face detected. Please try again.'})
        
        (x, y, w, h) = faces[0]
        face_roi = gray[y:y+h, x:x+w]
        resized_face = cv2.resize(face_roi, (50, 50))
        live_face_flat = resized_face.reshape(1, -1)
        
        predicted_user_id = knn.predict(live_face_flat)[0]
        
        if predicted_user_id != request.user.id:
            return JsonResponse({'success': False, 'error': 'Face does not match logged-in user. Verification failed.'})
        
        election = Election.objects.get(id=election_id)
        if Vote.objects.filter(voter=request.user, election=election).exists():
            return JsonResponse({'success': False, 'error': 'You have already voted in this election.'})

        candidate = Candidate.objects.get(id=candidate_id)
        Vote.objects.create(
            voter=request.user,
            election=election,
            candidate=candidate
        )
        
        return JsonResponse({'success': True, 'message': 'Vote cast successfully!'})
        
    except Exception as e:
        # --- THIS IS THE CORRECTED LINE ---
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'}, status=500)
        # --- END OF CORRECTION ---


# --- NEW PDF DOWNLOAD VIEW ---

@login_required
def download_slip(request, vote_id):
    try:
        vote = Vote.objects.get(id=vote_id, voter=request.user)
    except Vote.DoesNotExist:
        return HttpResponse("Vote not found or you do not have permission to view this slip.", status=404)
    
    template = get_template('slip.html')
    context = {'vote': vote}
    html = template.render(context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        filename = f"vote_slip_{vote.id}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    return HttpResponse("Error Rendering PDF", status=500)
