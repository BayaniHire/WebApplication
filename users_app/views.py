from django.shortcuts import render, redirect
from django.http import HttpResponse
import json
from . import views
from bayanihire_app.forms import AccountInformationForm
from bayanihire_app.models import (
    AccountInformation,
    AccountStorage,
    JobDetailsAndRequirements,
    InterviewStorage,
    ListOfApplicantsWithStatusAndCredentials
)
from bayanihire_app.forms import AdminAccountSetupForm
from datetime import datetime
from django.contrib.auth import authenticate
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse, Http404
from django.db.models import Q
import base64
import logging
import os
from django.conf import settings
from django.contrib import messages
from datetime import date
from django.db.models import Prefetch
from django.db.models.functions import Concat
from django.db.models import Value
from django.db import transaction
from django.urls import reverse
from django.db.models import Max
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password
from django.views.decorators.csrf import csrf_exempt
from bayanihire_app.models import AccountInformation
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.db import models
from bayanihire_app.models import JobDetailsAndRequirements
from django.contrib import messages
from django.db.models import Subquery, OuterRef
import random
import string
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.utils.crypto import get_random_string
from bayanihire_app.models import AccountInformation, OTPVerification
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth import logout
from django.utils.timezone import now, timedelta

def logout_view(request):
    logout(request)
    return redirect('Index')

def Index(request):
    return render(request, "index.html")

def login(request):
    return render(request, "logIn.html")

def Registration(request):
    return render(request, "registration.html")

def ForgotPassword(request):
    return render(request, "forgot_password.html")

def EmailConfirmation(request):
    return render(request, "email_confirmation.html")

def FchangePassword(request):
    return render(request, "force_change_password.html")

def Security(request):
    return render(request, "profile_forcechange.html")


######################INTERVIEWER###########################

def interviewer_applicants(request):
    # Get the interviewer's account ID from the session (assuming session is properly set after login)
    account_id = request.session.get('account_id')
    if not account_id:
        # Redirect to login if the account_id is not found in the session
        return redirect('login')

    # Retrieve the interviewer's own InterviewStorage entries
    interviews = InterviewStorage.objects.filter(account_id=account_id)

    # Fetch applicants linked to these interviews and qualified for interview
    qualified_applicants = ListOfApplicantsWithStatusAndCredentials.objects.filter(
        applicant_status='QUALIFIED',
        interview_applicant_id__in=interviews
    ).select_related('account', 'job', 'interview_applicant_id')

    # Prepare data for the template
    applicants_data = [
        {
            "full_name": f"{applicant.account.first_name} {applicant.account.middle_name or ''} {applicant.account.last_name}",
            "job_title": applicant.job.job_title,
            "job_company": applicant.job.job_company,
            "date_applied": applicant.submission_date,
            "interview_date": applicant.interview_applicant_id.interview_schedule_date if applicant.interview_applicant_id else None,
            "status": applicant.applicant_status,
            "applicant_status_id": applicant.applicant_status_id if applicant.applicant_status_id else None  # Ensure this line is added
        }
        for applicant in qualified_applicants
    ]

    return render(request, 'Applicants.html', {'applicants': applicants_data})

def interviewer_appointments(request):
    # Get the account ID from the session
    account_id = request.session.get('account_id')

    if not account_id:
        return redirect('login')  # Redirect to login if the account_id is not in session

    # Retrieve the account object based on the account_id from the session
    account = AccountInformation.objects.get(pk=account_id)

    # Fetch interview dates for the specific account
    interview_dates = InterviewStorage.objects.filter(account=account).values_list('interview_schedule_date', flat=True)

    # Pass the interview dates to the template
    context = {
        'interview_dates': interview_dates,
    }
    return render(request, 'Appointments.html', context)

def interviewer_editfeedback(request):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
    
    return render(request, 'EditFeedback.html')

def interviewer_feedback(request):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    if request.method == 'POST':
        # Assuming you have fields in your form named 'applicant_id', 'status', and 'feedback'
        applicant_id = request.POST.get('applicant_id')
        status = request.POST.get('status')
        feedback = request.POST.get('feedback')

        # Find the applicant and update their status and feedback
        applicant = ListOfApplicantsWithStatusAndCredentials.objects.get(applicant_status_id=applicant_id)
        applicant.interviewer_feedback_status = status
        applicant.interviewer_feedback = feedback
        applicant.save()

        # Optionally add a message indicating the feedback was successfully updated
        messages.success(request, 'Feedback updated successfully.')

    # Get all applicants or a subset based on certain criteria
    applicants = ListOfApplicantsWithStatusAndCredentials.objects.all()
    return render(request, 'Feedback.html', {'applicants': applicants})


# WEIN BAGO#
def interviewerhistory(request):
    user_id = request.session.get('user_id')  # Using 'user_id' for consistency
    if not user_id:
        return redirect('login')

    # Retrieve feedback entries for the interviewer with non-null feedback and 'PASSED'/'FAILED' statuses
    applicants_with_feedback = ListOfApplicantsWithStatusAndCredentials.objects.filter(
        interview_applicant_id__account_id=user_id,
        interviewer_feedback__isnull=False,
        interviewer_feedback_status__in=['PASSED', 'FAILED']
    ).select_related('account', 'job', 'interview_applicant_id').order_by('-submission_date')
    
    # Prepare the applicants' data for the template
    applicants_data = [
        {
            "full_name": f"{applicant.account.first_name} {applicant.account.middle_name or ''} {applicant.account.last_name}",
            "job_title": applicant.job.job_title,
            "job_company": applicant.job.job_company,
            "status": applicant.interviewer_feedback_status,
            "applicant_status_id": applicant.applicant_status_id
        }
        for applicant in applicants_with_feedback
    ]

    return render(request, 'History.html', {'applicants': applicants_data})
#WEIN BAGO#

def interviewer_profile(request):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    return render(request, 'Profile.html')

def interviewer_viewinfo(request, applicant_status_id):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    # Fetch the applicant using the provided applicant_status_id
    applicant = get_object_or_404(ListOfApplicantsWithStatusAndCredentials, applicant_status_id=applicant_status_id)

    # Fetch related account and job details
    account_info = applicant.account
    job_details = applicant.job

    # Prepare the uploaded files
    uploaded_files = applicant.file_metadata.split(",") if applicant.file_metadata else []
    uploaded_files = [file.strip() for file in uploaded_files]

    # Prepare context for rendering
    context = {
        'applicant': account_info,
        'job_details': job_details,
        'uploaded_files': uploaded_files,
        'submission_date': applicant.submission_date,
        'applicant_status': applicant.applicant_status,
        'applicant_status_id': applicant_status_id  # Ensure this is included
    }
    return render(request, 'ViewInfo.html', context)

##################INTERVIEWER######################


###################APPLICANT############################
def applicant_homepage(request):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    jobs = JobDetailsAndRequirements.objects.filter(job_status='ACTIVE')  # Fetch only active jobs
    context = {
        'jobs': jobs  # Pass the jobs to the template context
    }
    return render(request, 'Applicant_homepage.html', context)


def applicant_jobreq(request, job_id):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    job_details = get_object_or_404(JobDetailsAndRequirements, job_id=job_id)

    return render(request, 'Applicant_JobReq.html', {'job_details': job_details})

def applicant_fileupload(request, job_id):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    uploaded_files_display = []

    if request.method == 'GET':
        context = {'job_id': job_id, 'uploaded_files_display': uploaded_files_display}
        return render(request, 'Applicant_fileupload.html', context)

    if request.method == 'POST':
        uploaded_files = request.FILES.getlist('files')

        if not uploaded_files:
            return JsonResponse({"error": "No files selected."}, status=400)

        job_instance = get_object_or_404(JobDetailsAndRequirements, job_id=job_id)
        account_id = request.session.get('account_id')
        if not account_id:
            return JsonResponse({"error": "User must be logged in to upload files."}, status=403)

        account = get_object_or_404(AccountInformation, account_id=account_id)
        role_instance = get_object_or_404(AccountStorage, account=account)
        if role_instance.role.lower() != "applicant":
            return JsonResponse({"error": "Only applicants can upload files."}, status=403)

        # Initialize for combined file content and metadata
        file_metadata_list = []
        combined_file_content = b''

        # Process each uploaded file
        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name
            file_metadata_list.append(file_name)
            file_content = uploaded_file.read()
            
            # Debug: Log the file name and size
            print(f"Processing file: {file_name} with size: {len(file_content)} bytes")

            # Add the file content and a unique separator
            combined_file_content += file_content + b'<SEPARATOR>'
        
        # Remove the last separator if added
        if combined_file_content.endswith(b'<SEPARATOR>'):
            combined_file_content = combined_file_content[:-len(b'<SEPARATOR>')]

        # Debug: Log the combined content length and metadata
        print(f"Combined content length: {len(combined_file_content)}")
        print(f"File metadata list: {file_metadata_list}")

        # Save application with combined file contents and metadata
        new_application = ListOfApplicantsWithStatusAndCredentials(
            job=job_instance,
            role=role_instance,
            account=account,
            credentials=combined_file_content,
            file_metadata=', '.join(file_metadata_list),
            submission_date=timezone.now().date(),
            interview_applicant_id=None,
            applicant_status="UNDER REVIEW"
        )
        new_application.save()

        context = {
            'job_id': job_id,
            'uploaded_files_display': uploaded_files_display,
            'success_message': "Files successfully uploaded!"
        }
        return render(request, 'Applicant_fileupload.html', context)

    return JsonResponse({"error": "Invalid request method."}, status=405)



def applicant_applicationstatus(request):
    # Ensure the user is logged in using session data
    account_id = request.session.get('account_id')
    if not account_id:
        return redirect('login')  # Redirect to login if the user is not logged in

    # Fetch account information
    account = get_object_or_404(AccountInformation, account_id=account_id)

    # Retrieve applications related to the logged-in applicant, grouping by job
    applications = (
        ListOfApplicantsWithStatusAndCredentials.objects
        .filter(account=account)
        .select_related('job', 'interview_applicant_id') 
        .order_by('-submission_date') # Ensure you can access job-related fields
        .annotate(
            # Use Subquery to get the interview date for each application
            interview_schedule_date=Subquery(
                InterviewStorage.objects.filter(interview_applicant_id=Subquery(
                    ListOfApplicantsWithStatusAndCredentials.objects.filter(account=account)
                    .values('interview_applicant_id')[:1]
                )).values('interview_schedule_date')[:1]
            )
        )
        .values(
            'job__job_title',
            'job__job_date_published',
            'applicant_status',
            'submission_date',
            'interview_schedule_date',
            'applicant_status_id',
            'job__job_id'
        )
    )

    context = {
        'applications': applications,  # Pass the applications to the template
        'has_applications': applications.exists()  # Flag to check if applications exist
    }

    return render(request, 'Applicant_Applicationstatus.html', context)

def applicant_viewfileupload(request, applicant_status_id):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    # Retrieve the application details using the applicant_status_id
    application = get_object_or_404(ListOfApplicantsWithStatusAndCredentials, applicant_status_id=applicant_status_id)

    # Prepare to retrieve the uploaded files as binary
    uploaded_files = []

    # Split the file_metadata string into individual file names
    filenames = application.file_metadata.split(', ')  # Split by comma and space

    # Ensure you have the credentials data for each file
    if application.credentials:
        total_files_size = len(application.credentials)
        individual_file_size = total_files_size // len(filenames)  # Assume equal sizes for simplicity

        # Loop through each filename and prepare separate data
        for i, filename in enumerate(filenames):
            # Calculate the start and end index for each file's BLOB data
            start_index = i * individual_file_size
            end_index = start_index + individual_file_size if i < len(filenames) - 1 else total_files_size
            
            # Extract the specific file's binary data
            file_data = application.credentials[start_index:end_index]
            encoded_file = base64.b64encode(file_data).decode('utf-8')  # Base64 encode the specific part
            
            uploaded_files.append({
                'data': encoded_file,
                'metadata': filename,  # Use the individual filename
                'type': filename.split('.')[-1].lower(),  # Get file extension
            })

    # Pass the relevant information to the template
    context = {
        'application': application,
        'uploaded_files': uploaded_files,
    }

    return render(request, 'Applicant_Viewfileupload.html', context)



def applicant_interviewdetails(request, applicant_status_id):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    # Fetch interview details for the given applicant
    applicant = get_object_or_404(ListOfApplicantsWithStatusAndCredentials, applicant_status_id=applicant_status_id)

    # Check if the applicant is qualified
    if applicant.applicant_status == "QUALIFIED":
        # Check if interview details exist for the qualified applicant
        if applicant.interview_applicant_id:
            # If interview details exist, fetch them
            interview_details = {
                'interviewer_name': applicant.interview_applicant_id.interviewer_name,
                'schedule_date': applicant.interview_applicant_id.interview_schedule_date,
                'interview_message': applicant.admin_message,  # Use admin_message from ListOfApplicantsWithStatusAndCredentials
            }
            return render(request, 'Applicant_InterviewDetails.html', {
                'interview_details': interview_details
            })
        else:
            # If no interview schedule exists, show the message
            return render(request, 'Applicant_InterviewDetails.html', {
                'show_no_schedule_message': True
            })
    else:
        # If not qualified, show the message
        return render(request, 'Applicant_InterviewDetails.html', {
            'show_not_qualified_message': True
        })

def applicant_profile(request):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    return render(request, 'Applicant_profile.html')
###################APPLICANT############################



##########################Admin###############################################
logger = logging.getLogger(__name__)

def list_of_applicants(request):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    search_query = request.GET.get('search', '').strip()
    sort_order = request.GET.get('sort', 'asc')
    date_sort = request.GET.get('date_sort', 'asc')  # New parameter for date sorting
    rows_param = request.GET.get('rows', '5')
    rows_per_page = max(min(int(rows_param), 10), 1) if rows_param.isdigit() else 5

    query = Q(account__first_name__icontains=search_query) | Q(account__middle_name__icontains=search_query) | Q(account__last_name__icontains=search_query)
    if search_query:
        applicants = ListOfApplicantsWithStatusAndCredentials.objects.filter(query)
    else:
        applicants = ListOfApplicantsWithStatusAndCredentials.objects.all()

    # Handling sorting by name
    if sort_order == 'desc':
        applicants = applicants.order_by('-account__first_name', '-account__middle_name', '-account__last_name')
    else:
        applicants = applicants.order_by('account__first_name', 'account__middle_name', 'account__last_name')
    
    # Handling sorting by date
    if date_sort == 'desc':
        applicants = applicants.order_by('-submission_date')
    elif date_sort == 'asc':
        applicants = applicants.order_by('submission_date')

    paginator = Paginator(applicants, rows_per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'applicant_data': [{
            'no': (page_obj.number - 1) * rows_per_page + idx + 1,
            'full_name': f"{a.account.first_name} {a.account.middle_name or ''} {a.account.last_name}",
            'company': a.job.job_company,
            'position_applied': a.job.job_title,
            'date_applied': a.submission_date,
            'status': a.applicant_status,
            'applicant_status_id': a.applicant_status_id,
        } for idx, a in enumerate(page_obj)],
        'total_applicants': paginator.count,
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_order': sort_order,
        'date_sort': date_sort,  # Pass this to template for maintaining state
        'rows_per_page': rows_per_page,
    }
    return render(request, 'AdminView_1_Homepage_ListofApplicants.html', context)


def open_applicants(request, applicant_status_id):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    # Fetch the applicant using the provided applicant_status_id
    applicant = get_object_or_404(ListOfApplicantsWithStatusAndCredentials, applicant_status_id=applicant_status_id)

    # Fetch related account and job details
    account_info = applicant.account
    job_details = applicant.job

    # Prepare the list of uploaded files (from comma-separated metadata)
    uploaded_files = []
    filenames = applicant.file_metadata.split(", ") if applicant.file_metadata else []

    # Process credentials data to prepare each file as base64 encoded
    if applicant.credentials:
        total_files_size = len(applicant.credentials)
        individual_file_size = total_files_size // len(filenames) if filenames else 0

        for i, filename in enumerate(filenames):
            start_index = i * individual_file_size
            end_index = start_index + individual_file_size if i < len(filenames) - 1 else total_files_size
            file_data = applicant.credentials[start_index:end_index]
            encoded_file = base64.b64encode(file_data).decode('utf-8')
            
            uploaded_files.append({
                'data': encoded_file,
                'metadata': filename,
                'type': filename.split('.')[-1].lower(),
            })

    # Handle a file preview request for a specific file
    file_name_to_view = request.GET.get('view_file')
    if file_name_to_view:
        matching_file = next((file for file in uploaded_files if file['metadata'] == file_name_to_view), None)
        if not matching_file:
            raise Http404("File not found")

        # Return JSON response with file data and type for preview
        return JsonResponse({'file_data': matching_file['data'], 'file_type': matching_file['type']})

    # Render page with applicant and job details, status, and uploaded files
    context = {
        'applicant': account_info,
        'job_details': job_details,
        'uploaded_files': uploaded_files,
        'submission_date': applicant.submission_date,
        'applicant_status': applicant.applicant_status,
        'applicant_status_id': applicant_status_id
    }

    return render(request, 'AdminView_1_1_OpenApplicants.html', context)

def update_applicant_status(request, applicant_status_id):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    # Ensure the request method is POST
    if request.method == 'POST':
        # Fetch the applicant using the provided applicant_status_id
        applicant = get_object_or_404(ListOfApplicantsWithStatusAndCredentials, applicant_status_id=applicant_status_id)
        
        # Get the new status from the form
        new_status = request.POST.get('new_status')
        
        # Update the applicant's status in the database
        applicant.applicant_status = new_status
        applicant.save()
        
        messages.success(request, 'Applicant status updated successfully.')
        
        # Redirect to the dashboard after the update
        return redirect('list_of_applicants')  # Update this to your actual URL name for the dashboard

    return redirect('list_of_applicants')  # Redirect if not a POST request

def viewing_files(request, file_name):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    # Construct the full file path
    file_path = os.path.join(settings.MEDIA_ROOT, file_name)

    # Debugging: Print the file path to console
    print(f"Trying to access file at: {file_path}")

    # Check if the file exists
    if not os.path.exists(file_path):
        raise Http404("File does not exist")

    context = {
        'file_name': file_name,
        'file_path': file_path
    }

    return render(request, 'AdminView_1_2_ViewingFiles.html', context)

def list_of_jobs(request):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    search_query = request.GET.get('search', '').strip()
    sort_order = request.GET.get('sort', 'title_asc')  # Default sort by job title ascending
    rows_param = request.GET.get('rows', '5')  # Set default rows to 5
    rows_per_page = max(min(int(rows_param), 10), 1) if rows_param.isdigit() else 5

    query = Q(job_title__icontains=search_query) | Q(job_company__icontains=search_query)
    jobs = JobDetailsAndRequirements.objects.filter(query)

    # Apply sorting based on the sort_order
    if sort_order == 'title_desc':
        jobs = jobs.order_by('-job_title')
    elif sort_order == 'company_asc':
        jobs = jobs.order_by('job_company')
    elif sort_order == 'company_desc':
        jobs = jobs.order_by('-job_company')
    elif sort_order == 'date_asc':
        jobs = jobs.order_by('job_date_published')
    elif sort_order == 'date_desc':
        jobs = jobs.order_by('-job_date_published')
    else:
        jobs = jobs.order_by('job_title')

    paginator = Paginator(jobs, rows_per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    start_index = (page_obj.number - 1) * rows_per_page + 1

    context = {
        'jobs': page_obj,
        'active_jobs_count': JobDetailsAndRequirements.objects.filter(job_status="ACTIVE").count(),
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_order': sort_order,
        'rows_per_page': rows_per_page,  # Make sure to pass this back to the template
        'start_index': start_index 
    }
    return render(request, 'AdminView_2_ListofJobs.html', context)

def edit_job_details(request, job_id):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    job = get_object_or_404(JobDetailsAndRequirements, pk=job_id)

    if request.method == 'POST':
        # Update fields with form data
        job.job_title = request.POST.get('job_title')
        job.job_company = request.POST.get('company')
        job.job_description = request.POST.get('job_description')
        job.job_benefits = request.POST.get('job_benefits')
        job.job_requirements = request.POST.get('job_requirements')
        job.job_status = request.POST.get('status')

        # Update the date field if a new date is provided
        new_date = request.POST.get('date')
        if new_date:
            job.job_date_published = new_date

        # Save changes to the database
        job.save()
        return redirect('list_of_jobs')

    # Format the date for display, default to today if no date is set
    job_date = job.job_date_published or date.today()
    job_date = job_date.strftime("%Y-%m-%d")  # Format as YYYY-MM-DD for HTML input

    # Count the number of active jobs
    active_jobs_count = JobDetailsAndRequirements.objects.filter(job_status="ACTIVE").count()

    return render(request, 'AdminView_2_1_EditJobDetails.html', {
        'job': job,
        'job_date': job_date,
    })
    

def create_job_details(request):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    today_date = date.today().strftime("%Y-%m-%d")  # Format today's date as YYYY-MM-DD
    return render(request, 'AdminView_2_2_CreateJobDetails.html', {'today_date': today_date})


def qualification(request):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    interviewers = InterviewStorage.objects.select_related('account')
    grouped_interviewers = {}

    for interviewer in interviewers:
        account_id = interviewer.account_id
        interviewer_name = interviewer.interviewer_name
        if account_id not in grouped_interviewers:
            grouped_interviewers[account_id] = {
                "interviewer_id": interviewer.account_id,
                "interviewer_name": interviewer_name,
                "schedule_dates": []
            }
        grouped_interviewers[account_id]["schedule_dates"].append(str(interviewer.interview_schedule_date))

    interviewer_data = list(grouped_interviewers.values())

    applicants = (
        ListOfApplicantsWithStatusAndCredentials.objects.select_related('account', 'job')
        .filter(applicant_status='FOR INTERVIEW')
        .values(
            'account__first_name', 'account__middle_name', 'account__last_name',
            'job__job_title', 'job__job_company'
        )
    )

    applicant_data = [
        {
            "full_name": f"{applicant['account__first_name']} {applicant['account__middle_name'] or ''} {applicant['account__last_name']}".strip(),
            "job_title": applicant['job__job_title'],
            "job_company": applicant['job__job_company']
        }
        for applicant in applicants
    ]

    if request.method == 'POST':
        # Capture the selected applicant and interviewer details
        selected_applicant_full_name = request.POST.get('selected_applicant_full_name')
        selected_job_details = request.POST.get('selected_job_details')
        
        # Redirect to the send_schedule view with the selected data
        return redirect('send_schedule', applicant_name=selected_applicant_full_name, job_details=selected_job_details)

    return render(request, 'AdminView_3_Qualification.html', {
        'interviewers': interviewer_data,
        'applicants': applicant_data
    })
    
def send_schedule(request):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
      # Fetch all applicants who are set for interview
    applicants = ListOfApplicantsWithStatusAndCredentials.objects.filter(
        applicant_status='FOR INTERVIEW'
    ).select_related('account', 'job', 'interview_applicant_id')  # assuming foreign key is loaded properly

    # Prepare data for display in template
    applicant_data = [
        {
            "full_name": f"{applicant.account.first_name} {applicant.account.middle_name or ''} {applicant.account.last_name}".strip(),
            "job_title": applicant.job.job_title,
            "job_company": applicant.job.job_company,
            "applicant_status_id": applicant.applicant_status_id,
            "interview_applicant_id": applicant.interview_applicant_id_id if applicant.interview_applicant_id else None
        }
        for applicant in applicants
    ]
    
    if request.method == "POST":
        interviewer_name = request.POST.get('interviewer_name')
        schedule_date = request.POST.get('selected_schedule_date')
        
    
       
        return render(request, 'AdminView_3_1_Send.html', {
            'interviewer_name': interviewer_name,
            'schedule_date': schedule_date,
            'applicants': applicant_data  # Include updated applicants in the response
        })
# GET request: Render page with initial applicant data
    return render(request, 'AdminView_3_1_Send.html', {
        'applicants': applicant_data
    })

def confirm_send_schedule(request):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    if request.method == "POST":
        interviewer_name = request.POST.get('interviewer_name')
        schedule_date = request.POST.get('schedule_date')
        interview_message = request.POST.get('interview_message')
        applicant_ids = request.POST.getlist('applicant_ids[]')  # Note the brackets to fetch a list

        # Find interview instance or handle error
        interview_instance = InterviewStorage.objects.filter(interviewer_name=interviewer_name, interview_schedule_date=schedule_date).first()
        if not interview_instance:
            return redirect('send_schedule')  # Consider adding error messaging here

        with transaction.atomic():
            for applicant_id in applicant_ids:
                applicant = get_object_or_404(ListOfApplicantsWithStatusAndCredentials, applicant_status_id=applicant_id)
                applicant.interview_applicant_id = interview_instance
                applicant.applicant_schedule_date = schedule_date
                applicant.admin_message = interview_message
                applicant.applicant_status = 'QUALIFIED'
                applicant.save()

        return redirect('list_of_applicants')  # Redirect to a confirmation or success page
    return redirect('send_schedule')


def open_schedule_list(request):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    interviewer_name = request.GET.get('interviewer', None)
    search_query = request.GET.get('search', '').strip()
    sort_order = request.GET.get('date_sort', 'asc')
    rows_param = request.GET.get('rows', '5')
    rows_per_page = max(min(int(rows_param), 10), 1) if rows_param.isdigit() else 5

    # Base queryset of applicants
    applicants = ListOfApplicantsWithStatusAndCredentials.objects.none()

    if interviewer_name:
        # Filter applicants by the selected interviewer
        interviews = InterviewStorage.objects.filter(interviewer_name=interviewer_name)
        applicants = ListOfApplicantsWithStatusAndCredentials.objects.filter(
            interview_applicant_id__in=interviews,
            account__first_name__icontains=search_query
        ).distinct()

        # Apply date sorting if an interviewer is selected
        if sort_order == 'desc':
            applicants = applicants.order_by('-applicant_schedule_date')
        else:
            applicants = applicants.order_by('applicant_schedule_date')

    # Pagination
    paginator = Paginator(applicants, rows_per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Retrieve distinct interviewers
    interviewer_ids = InterviewStorage.objects.values('interviewer_name').annotate(max_id=Max('interview_applicant_id')).values('max_id')
    interviewers = InterviewStorage.objects.filter(interview_applicant_id__in=interviewer_ids)

    # Context for rendering
    context = {
        'applicants': page_obj,
        'interviewers': interviewers,
        'search_query': search_query,
        'interviewer_name': interviewer_name,
        'sort_order': sort_order,
        'rows_per_page': rows_per_page,
        'page_obj': page_obj,
    }

    return render(request, 'AdminView_3_2_OpenScheduleList.html', context)

def schedule(request):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    today = date.today()
    search_query_interviewer = request.GET.get('search_interviewer', '').strip()
    search_query_schedule = request.GET.get('search_schedule', '').strip()  # Ensure this variable is defined

    interviewers = AccountStorage.objects.filter(role='interviewer').select_related('account')
    if search_query_interviewer:
        interviewers = interviewers.filter(
            Q(account__first_name__icontains=search_query_interviewer) |
            Q(account__middle_name__icontains=search_query_interviewer) |
            Q(account__last_name__icontains=search_query_interviewer)
        )

    if request.method == "POST":
        selected_interviewer_name = request.POST.get('selected_interviewer')
        interview_date = request.POST.get('interview_date')

        if interview_date:
            interview_date_obj = date.fromisoformat(interview_date)
            if interview_date_obj < today:
                messages.error(request, 'The selected date must be today or in the future.')
                return redirect('schedule')

        selected_interviewer = interviewers.filter(
            account__first_name__icontains=selected_interviewer_name.split()[0],
            account__last_name__icontains=selected_interviewer_name.split()[-1]
        ).first()

        if selected_interviewer:
            InterviewStorage.objects.create(
                account=selected_interviewer.account,
                role=selected_interviewer,
                interview_schedule_date=interview_date_obj,
                interviewer_name=selected_interviewer_name
            )
            messages.success(request, 'Interview scheduled successfully.')
            return redirect('schedule')
        else:
            messages.error(request, 'Selected interviewer not found.')
            return redirect('schedule')

    # Pagination for interviewers
    rows_interviewer = int(request.GET.get('rows_interviewer', 5))
    page_number_interviewer = request.GET.get('page_interviewer', 1)
    interviewer_paginator = Paginator(interviewers, rows_interviewer)
    page_obj_interviewer = interviewer_paginator.get_page(page_number_interviewer)

    # Handling interview schedules display setup
    interview_data = InterviewStorage.objects.select_related('account').order_by('-interview_schedule_date')
    formatted_interview_data = [
        {
            "name": f"{entry.account.first_name} {entry.account.middle_name} {entry.account.last_name}".strip(),
            "date": entry.interview_schedule_date
        } for entry in interview_data
    ]

    # Pagination for interview schedules
    rows_schedule = int(request.GET.get('rows_schedule', 5))
    page_number_schedule = request.GET.get('page_schedule', 1)
    schedule_paginator = Paginator(formatted_interview_data, rows_schedule)
    page_obj_schedule = schedule_paginator.get_page(page_number_schedule)

    context = {
        'interviewer_names': page_obj_interviewer,
        'formatted_interview_data': page_obj_schedule,
        'search_query_interviewer': search_query_interviewer,
        'search_query_schedule': search_query_schedule,
        'rows_interviewer': rows_interviewer,
        'rows_schedule': rows_schedule,
        'page_obj_interviewer': page_obj_interviewer,
        'page_obj_schedule': page_obj_schedule,
    }
    return render(request, 'AdminView_4_Schedule.html', context)


def schedule_view(request):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    # Retrieve interview records with interviewer names and scheduled dates
    interview_data = InterviewStorage.objects.select_related('account').values(
        'account__first_name', 'account__middle_name', 'account__last_name', 'interview_schedule_date'
    )

    # Format interviewer names and dates for display
    formatted_interview_data = [
        {
            "name": f"{entry['account__first_name'] or ''} {entry['account__middle_name'] or ''} {entry['account__last_name'] or ''}".strip(),
            "date": entry['interview_schedule_date']
        }
        for entry in interview_data
    ]

    # Pass formatted interview data to the template
    context = {
        'formatted_interview_data': formatted_interview_data,
    }
    return render(request, 'AdminView_4_Schedule.html', context)

def feedback(request):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    search_query = request.GET.get('search', '').strip()
    sort_order = request.GET.get('name_sort', 'asc')
    rows_param = request.GET.get('rows', '5')
    rows_per_page = max(min(int(rows_param), 10), 1) if rows_param.isdigit() else 5

    # Base queryset of applicants excluding those with None or empty interviewer feedback status
    applicants = ListOfApplicantsWithStatusAndCredentials.objects.select_related('account', 'job') \
        .exclude(interviewer_feedback_status__isnull=True) \
        .exclude(interviewer_feedback_status='')

    # Filter by search query if provided
    if search_query:
        applicants = applicants.filter(
            account__first_name__icontains=search_query
        )

    # Sort applicants by name
    if sort_order == 'desc':
        applicants = applicants.order_by('-account__first_name', '-account__last_name')
    else:
        applicants = applicants.order_by('account__first_name', 'account__last_name')

    # Pagination
    paginator = Paginator(applicants, rows_per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'AdminView_5_Feedback.html', {
        'applicants': page_obj,
        'search_query': search_query,
        'sort_order': sort_order,
        'rows_per_page': rows_per_page,
        'page_obj': page_obj,
    })

@require_http_methods(["GET", "POST"])
def view_feedback(request, applicant_status_id):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    # Fetch the specific applicant using the provided ID
    applicant = get_object_or_404(ListOfApplicantsWithStatusAndCredentials, pk=applicant_status_id)
    
    if request.method == "POST":
        # Update the applicant's status with data from the form
        new_status = request.POST.get('applicant_status')
        if new_status:
            applicant.applicant_status = new_status
            applicant.save()
            # Redirect to the same page to show updated status
            return redirect('feedback')

    # For GET requests or initial form rendering
    interviewer_name = applicant.interview_applicant_id.interviewer_name if applicant.interview_applicant_id else "No interviewer assigned"
    context = {
        'interviewer_name': interviewer_name,
        'applicant_name': f"{applicant.account.first_name} {applicant.account.last_name}",
        'interview_status': applicant.interviewer_feedback_status,
        'interview_feedback': applicant.interviewer_feedback,
        'applicant_status_id': applicant_status_id  # Needed to build the form action URL
    }
    
    return render(request, 'AdminView_5_1_ViewFeedback.html', context)



def adminprofile(request):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    # Assuming the user's ID is stored in session
    account_id = request.session.get('account_id')
    user = get_object_or_404(AccountInformation, account_id=account_id)
    
    if request.method == "POST":
        # Change Password Logic
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Check if the current password matches
        if user.password != current_password:
            messages.error(request, "Current password is incorrect.")
        elif new_password == current_password:
            messages.error(request, "New password must be different from the current password.")
        elif new_password != confirm_password:
            messages.error(request, "New password and confirm password do not match.")
        else:
            # Update the password
            user.password = new_password
            user.save()
            messages.success(request, "Password updated successfully.")
            return redirect('adminprofile')

    # Display profile info
    context = {
        'username': user.username,
        'full_name': f"{user.first_name} {user.middle_name or ''} {user.last_name}",
        'email': user.email
    }
    return render(request, 'AdminView_6_Profile.html', context)

def add_accounts(request):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    if request.method == 'POST':
        # Birthday validation
        birthday = request.POST.get('birthday')
        if birthday:
            birth_date = date.fromisoformat(birthday)
            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            if age < 18:
                messages.error(request, "Users must be at least 18 years old.")
                return redirect('add_accounts')
        
        # Continue processing the form if email and age are valid
    return render(request, 'AdminView_6_2_AddAccounts.html')

def manage_accounts(request):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    # Fetch search, sort, and rows parameters from GET
    search_query = request.GET.get('search', '').strip()
    sort_order = request.GET.get('sort', 'asc')
    rows_param = request.GET.get('rows', '5')

    # Set rows per page with a default of 5
    rows_per_page = int(rows_param) if rows_param.isdigit() and int(rows_param) > 0 else 5
    rows_per_page = min(rows_per_page, 15)

    # Filter accounts based on search query
    if search_query:
        accounts = AccountStorage.objects.filter(account__username__icontains=search_query)
    else:
        accounts = AccountStorage.objects.all()

    # Sort accounts based on sort order
    if sort_order == 'desc':
        accounts = accounts.order_by('-account__username')
    else:
        accounts = accounts.order_by('account__username')

    # Check if there are no matching accounts
    no_match = not accounts.exists()

    # Reactivate or deactivate accounts based on button press
    if request.method == "POST":
        action = request.POST.get('action')
        role_id = int(request.POST.get('role_id'))
        account_storage = AccountStorage.objects.get(role_id=role_id)

        # Update the account status based on the action
        if action == 'deactivate' and account_storage.account_status == 'active':
            account_storage.account_status = 'deactivated'
            messages.success(request, "Updated status to deactivated.")
        elif action == 'reactivate' and account_storage.account_status == 'deactivated':
            account_storage.account_status = 'active'
            messages.success(request, "Updated status to active.")
        elif account_storage.account_status == 'active':
            messages.info(request, "The account is already active.")

        account_storage.save()

        # Redirect to the same page with all parameters preserved
        query_params = request.GET.copy()  # Copies all current GET parameters
        return HttpResponseRedirect(f"{reverse('manage_accounts')}?{query_params.urlencode()}")

    # Pagination
    paginator = Paginator(accounts, rows_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_order': sort_order,
        'rows_param': rows_param,
        'no_match': no_match,  # Pass the no_match flag to the template
    }
    return render(request, 'AdminView_6_1_manage_accounts.html', context)

def admin_interviewer_account_setup(request):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    if request.method == 'POST':
        try:
            # Get the form data
            role = request.POST.get('role').lower()
            birthday = request.POST.get('birthday')
            gender = request.POST.get('gender')
            first_name = request.POST.get('first_name')
            middle_name = request.POST.get('middle_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')

            # Ensure all required fields are provided
            if not (role and birthday and gender and first_name and last_name and email):
                return render(request, 'users_app/AdminView_6_2_AddAccounts.html', {"message": "Missing required fields. Please fill out the form completely."})

            # Check if the birthday is not empty and compute age
            birth_date = datetime.strptime(birthday, "%Y-%m-%d")
            today = datetime.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

            # Generate default username and password
            base_username = f"{first_name.lower().replace(' ', '')}@bynhr.com"
            password = last_name.lower().replace(' ', '')  # Use the last name as the default password and remove spaces

            # Check if the username already exists and make it unique if needed
            username = base_username
            count = 1
            while AccountInformation.objects.filter(username=username).exists():
                username = f"{base_username}_{count}"
                count += 1

            # Step 1: Save data to AccountInformation, including the email field
            account_info = AccountInformation(
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                birth_date=birth_date,
                gender=gender,
                username=username,
                password=password,
                email=email,
                age=age
            )
            account_info.save()  # Save to the database

            # Step 2: Save data to AccountStorage with the role
            account_storage = AccountStorage(
                account=account_info,  # Link to the saved AccountInformation instance
                role=role,
                account_status='new'  # Default status or customize as needed
            )
            account_storage.save()  # Save to the database

            # Redirect to the profile admin page
            messages.success(request, f"Account created successfully with username: {username}")
            return redirect('adminprofile')

        except Exception as e:
            # Handle any errors
            return render(request, 'users_app/AdminView_6_2_AddAccounts.html', {"message": f"An error occurred: {str(e)}"})

    # Render the form if it's not a POST request
    return render(request, 'users_app/AdminView_6_2_AddAccounts.html')

def admin_creatingjob(request):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    if request.method == 'POST':
        # Get the form data
        status = request.POST.get('status')
        job_title = request.POST.get('job_title')
        job_benefits = request.POST.get('job_benefits')
        company = request.POST.get('company')
        job_description = request.POST.get('job_description')
        job_requirements = request.POST.get('job_requirements')

        # Set the job_date_published to today's date
        job_date_published = datetime.now().date()

        # Fetch the account ID from the session
        account_id = request.session.get('account_id')

        # Ensure the account ID is present and valid
        if account_id:
            account = get_object_or_404(AccountInformation, account_id=account_id)
        else:
            return redirect('login')  # Redirect to login if no user is logged in
        
         # Validate required fields
        if not (status and job_title and company and job_description and job_requirements):
            return render(request, 'users_app/create_job.html', {'error': 'All fields are required'})
        
        # Create and save the job entry
        new_job = JobDetailsAndRequirements(
            account=account,
            job_title=job_title,
            job_company=company,
            job_description=job_description,
            job_benefits=job_benefits,
            job_requirements=job_requirements,
            job_status=status,
            job_date_published=job_date_published
        )
        new_job.save()

        # Redirect to a relevant page (e.g., list of jobs) after saving
        return redirect('list_of_jobs')  # Adjust to your desired URL

    # Render the form if it's a GET request
    return render(request, 'users_app/create_job.html')

###########################ADMIN RETRIEVAL####################################

#WEIN BAGO DAGDAG 11-11-2024
from django.contrib import messages

def interviewer_feedback(request):
    account_id = request.session.get('account_id')
    if not account_id:
        return redirect('login')

    if request.method == 'POST':
        applicant_id = request.POST.get('applicant_id')
        status = request.POST.get('status')
        feedback = request.POST.get('feedback')

        if not applicant_id:
            messages.error(request, "Please select an applicant.")
            return redirect('interviewer_feedback')

        # Find and update the applicant's status and feedback
        applicant = ListOfApplicantsWithStatusAndCredentials.objects.get(applicant_status_id=applicant_id)
        applicant.interviewer_feedback_status = status
        applicant.interviewer_feedback = feedback
        applicant.save()

        return redirect('INTappointments')

    interviews = InterviewStorage.objects.filter(account_id=account_id)
    applicants = ListOfApplicantsWithStatusAndCredentials.objects.filter(
        interview_applicant_id__in=interviews,
        applicant_status='QUALIFIED'
    ).exclude(
        interviewer_feedback_status__in=['PASSED', 'FAILED']
    ).select_related('account', 'job', 'interview_applicant_id')

    return render(request, 'Feedback.html', {'applicants': applicants})

def interviewer_editfeedback(request, applicant_status_id):
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    # Retrieve the applicant using the applicant_status_id
    applicant = ListOfApplicantsWithStatusAndCredentials.objects.get(applicant_status_id=applicant_status_id)

    # If the request is a POST, we are saving the updated feedback
    if request.method == 'POST':
        status = request.POST.get('status')
        feedback = request.POST.get('feedback')

        # Update the applicant's feedback status and remarks
        applicant.interviewer_feedback_status = status
        applicant.interviewer_feedback = feedback
        applicant.save()

        # Redirect to feedback history page after updating
        return redirect('INThistory')  # Adjust this URL to your feedback history page URL

    # Pass the applicant data to the template for pre-filling
    return render(request, 'EditFeedback.html', {'applicant': applicant})
    # Retrieve the applicant using the applicant_status_id
    applicant = ListOfApplicantsWithStatusAndCredentials.objects.get(applicant_status_id=applicant_status_id)

    # If the request is a POST, we are saving the feedback
    if request.method == 'POST':
        status = request.POST.get('status')
        feedback = request.POST.get('feedback')

        # Update the applicant's feedback status and remarks
        applicant.interviewer_feedback_status = status
        applicant.interviewer_feedback = feedback
        applicant.save()

        # Redirect to feedback history page after updating
        return redirect('INThistory')  # Adjust this URL to your feedback history page URL

    # Pass the applicant data to the template for pre-filling
    return render(request, 'EditFeedback.html', {'applicant': applicant})

def interviewer_applicants(request):
    # Get the interviewer's account ID from the session (assuming session is properly set after login)
    account_id = request.session.get('account_id')
    if not account_id:
        # Redirect to login if the account_id is not found in the session
        return redirect('login')

    # Retrieve the interviewer's own InterviewStorage entries
    interviews = InterviewStorage.objects.filter(account_id=account_id)

    # Fetch applicants linked to these interviews and qualified for interview
    qualified_applicants = ListOfApplicantsWithStatusAndCredentials.objects.filter(
        applicant_status='QUALIFIED',
        interview_applicant_id__in=interviews
    ).select_related('account', 'job', 'interview_applicant_id')

    # Prepare data for the template
    applicants_data = [
        {
            "full_name": f"{applicant.account.first_name} {applicant.account.middle_name or ''} {applicant.account.last_name}",
            "job_title": applicant.job.job_title,
            "job_company": applicant.job.job_company,
            "date_applied": applicant.submission_date,
            "interview_date": applicant.interview_applicant_id.interview_schedule_date if applicant.interview_applicant_id else None,
            "status": applicant.applicant_status,
            "applicant_status_id": applicant.applicant_status_id if applicant.applicant_status_id else None  # Ensure this line is added
        }
        for applicant in qualified_applicants
    ]

    return render(request, 'Applicants.html', {'applicants': applicants_data})

def interviewer_history(request):
    account_id = request.session.get('account_id')
    if not account_id:
        return redirect('login')

    # Retrieve interview sessions associated with the interviewer
    interviews = InterviewStorage.objects.filter(account_id=account_id)
    
    # Include only applicants with feedback status 'PASSED' or 'FAILED'
    applicants_with_feedback = ListOfApplicantsWithStatusAndCredentials.objects.filter(
        interview_applicant_id__in=interviews,
        interviewer_feedback_status__in=['PASSED', 'FAILED']
    ).select_related('account', 'job', 'interview_applicant_id')
    
    # Prepare the applicants' data for the template
    applicants_data = [
        {
            "full_name": f"{applicant.account.first_name} {applicant.account.middle_name or ''} {applicant.account.last_name}",
            "job_title": applicant.job.job_title if applicant.job else "No job title",
            "job_company": applicant.job.job_company if applicant.job else "No job company",
            "status": applicant.interviewer_feedback_status or "No status",
            "applicant_status_id": applicant.applicant_status_id
        }
        for applicant in applicants_with_feedback
    ]

    return render(request, 'History.html', {'applicants': applicants_data})


def interviewer_profile(request):
    # Get the interviewer's account ID from the session
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response
        
    account_id = request.session.get('account_id')
    user = get_object_or_404(AccountInformation, account_id=account_id)

    if request.method == "POST":
        # Change Password Logic
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Check if the current password matches
        if user.password != current_password:
            messages.error(request, "Current password is incorrect.")
        elif new_password == current_password:
            messages.error(request, "New password must be different from the current password.")
        elif new_password != confirm_password:
            messages.error(request, "New password and confirm password do not match.")
        else:
            # Update the password
            user.password = new_password
            user.save()
            messages.success(request, "Password updated successfully.")
            return redirect('INTprofile')  # Redirect to the interviewer profile page

    # Display profile info
    context = {
        'username': user.username,
        'full_name': f"{user.first_name} {user.middle_name or ''} {user.last_name}",
        'email': user.email
    }
    return render(request, 'Profile.html', context)

# 11-11-2024

############################index##########################################
def ensure_authenticated(request):
    if 'account_id' not in request.session:
        messages.error(request, "You must log in first.")
        return redirect('login')
    return None

def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            
            # Authenticate the user
            account = AccountInformation.objects.get(username=username, password=password)
            print("Account found:", account)  # Debug: Print the retrieved account
            
            # Retrieve the account status from AccountStorage using the foreign key
            account_storage = AccountStorage.objects.filter(account=account).first()
            print("Account Storage found:", account_storage)
            
            if account_storage:
                # Check the account status
                if account_storage.account_status == 'new':
                    # Store account ID in the session to reference it in change_password view
                    request.session['account_id'] = account.account_id
                    return redirect('Security')
                
                elif account_storage.account_status == 'deactivate':
                    return render(request, 'login.html', {"message": "Account is deactivated. Please contact support."})
                
                # If account_status is neither 'new' nor 'deactivate', proceed to role-based redirection
                request.session['account_id'] = account.account_id
                
                # Redirect based on role
                if account_storage.role == 'applicant':
                    return redirect('homepage')
                elif account_storage.role == 'admin':
                    return redirect('list_of_applicants')
                elif account_storage.role == 'interviewer':
                    return redirect('INTappointments')
                else:
                    return render(request, 'login.html', {"message": "Invalid role. Access denied."})
            else:
                return render(request, 'login.html', {"message": "Incorrect username or password."})
        
        except AccountInformation.DoesNotExist:
            return render(request, 'login.html', {"message": "Incorrect username or password."})

    return render(request, 'login.html')

def Registration(request):    
    if request.method == 'POST':
        form = AccountInformationForm(request.POST)
        if form.is_valid():
            account_info = form.save()  # Save the AccountInformation instance
            
            # Create the corresponding AccountStorage entry
            AccountStorage.objects.create(
                account=account_info,  # Link to the account
                role='applicant',  # Set role as 'applicant'
                account_status='active'  # Set account status as 'active'
            )
            
            # Redirect to a success page or login
            return redirect('login')  # Change 'success_page' to the actual success page you have
    else:
        form = AccountInformationForm()
    
    return render(request, 'registration.html', {'form': form})
    
def change_password(request):
    # Only allow POST requests and check if account_id exists in the session
    if request.method == 'POST' and 'account_id' in request.session:
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        # Fetch the account by account_id stored in the session
        account_id = request.session['account_id']
        account = AccountInformation.objects.get(account_id=account_id)

        # Check if the new password is the same as the old password
        if new_password == account.password:
            messages.error(request, "New password cannot be the same as the old password.")
            return redirect('Security')

        # Verify the password fields match
        if new_password == confirm_password:
            # Update the account's password
            account.password = new_password
            account.save()
            
            # Update account status in AccountStorage
            account_storage = AccountStorage.objects.get(account=account)
            account_storage.account_status = 'active'
            account_storage.save()
            
            # Redirect based on role after password change
            if account_storage.role == 'applicant':
                return redirect('homepage')
            elif account_storage.role == 'admin':
                return redirect('list_of_applicants')
            elif account_storage.role == 'interviewer':
                return redirect('INTappointments')
            else:
                return render(request, 'login.html', {"message": "Invalid role. Access denied."})
        else:
            messages.error(request, "Passwords do not match. Please try again.")
            return redirect('Security')
        

    return redirect('login')
######################ito yung udpate password sa mga account#######################################################################3
def update_password(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            account_id = data.get('account_id') or request.session.get('account_id')  # Fallback to session
            current_password = data.get('current_password')
            new_password = data.get('new_password')

            print("Account ID received in view:", account_id)  # Debugging: print the account_id

            # Check if account_id is None (missing or not provided)
            if account_id is None:
                return JsonResponse({'success': False, 'error': 'Account ID is missing in the request.'})

            # Ensure new_password and current_password are provided
            if not new_password or not current_password:
                return JsonResponse({'success': False, 'error': 'New password or current password is missing.'})

            # Retrieve the account
            try:
                account = AccountInformation.objects.get(account_id=account_id)

                # Verify that the current password matches
                if account.password != current_password:
                    return JsonResponse({'success': False, 'error': 'Current password is incorrect.'})

                # Update the password
                account.password = new_password  # Store password in plain text
                account.save()
                return JsonResponse({'success': True})

            except AccountInformation.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Account not found with the provided ID.'})

        except Exception as e:
            return JsonResponse({'success': False, 'error': f'An unexpected error occurred: {str(e)}'})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

def Index(request):  # Capitalize the function name to match the URL pattern
    companies = JobDetailsAndRequirements.objects.values('job_company').annotate(job_count=models.Count('job_id'))
    
    context = {
        'companies': companies
    }
    return render(request, 'index.html', context)


# Email Function
@csrf_exempt
def verify_otp(request):
    if request.method == 'POST':
        print(f"Session Email: {request.session.get('email')}")
        otp_code = request.POST.get('otp_code')
        email = request.session.get('email')

        if not email:
            return render(request, 'email_confirmation.html', {
                'error': 'Session expired. Please restart the process.'
            })

        try:
            # Fetch the latest unused OTP for the email
            otp_record = OTPVerification.objects.filter(email=email, is_used=False).latest('created_at')

            # Validate OTP and expiration
            if otp_record.otp != otp_code:
                return render(request, 'email_confirmation.html', {
                    'error': 'Invalid OTP. Please try again.'
                })

            if otp_record.is_expired():
                return render(request, 'email_confirmation.html', {
                    'error': 'OTP has expired. Please request a new one.'
                })

            # Mark OTP as used only after successful verification
            otp_record.is_used = True
            otp_record.save()

            # Store account_id in the session for further actions
            request.session['account_id'] = otp_record.account.account_id

            # Redirect to the password reset page
            return redirect('force_change_password')

        except OTPVerification.DoesNotExist:
            return render(request, 'email_confirmation.html', {
                'error': 'No valid OTP found. Please request a new code.'
            })

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})





def generate_otp(email):
    try:
        account = AccountInformation.objects.get(email=email)
    except AccountInformation.DoesNotExist:
        return {"success": False, "error": "Account not found for the provided email."}

    # Check for an existing unused OTP
    existing_otp = OTPVerification.objects.filter(email=email, is_used=False).first()
    if existing_otp:
        # Reuse the existing OTP
        return {"success": True, "otp": existing_otp.otp}

    # Generate a new OTP
    otp = ''.join(random.choices(string.digits, k=2)) + ''.join(random.choices(string.ascii_letters, k=4))
    
    # Create a new OTP record
    otp_record = OTPVerification.objects.create(
        email=email,
        otp=otp,
        created_at=now(),
        account=account  # Ensure the account is linked
    )
    return {"success": True, "otp": otp_record.otp}


    

def force_change_password(request):
    return render(request, 'force_change_password.html')

def send_otp_to_email(email, otp):
    # Fetch or generate a new OTP
    otp_data = generate_otp(email)
    if not otp_data["success"]:
        raise ValueError(otp_data["error"])

    otp = otp_data["otp"]

    
    # Construct the email subject and HTML content
    subject = 'Your OTP Code for BayaniHire'
    html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; text-align: center; margin: 20px; padding: 20px;background-color:#FFFFFF; border: 1px solid #ddd; border-radius: 10px;">
            <div>
                <h1 style="color:#5c332e;">BayaniHire</h1>
                <p style="color: #000000;">Dear User,</p>
                <p style="color:  #000000;">Your One-Time Password (OTP) is:</p>
                <h2 style="color: red;">{otp}</h2>
                <p style="color:  #000000;">Please use this OTP to complete your login process. Do not share this code with anyone.</p>
                <p style="color:  #000000;">Thank you for using BayaniHire!</p>
            </div>
        </body>
        </html>
    """

    # Create the email
    email_message = EmailMultiAlternatives(
        subject=subject,
        body=f"Your OTP code is: {otp}",  # Fallback plain text
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    email_message.attach_alternative(html_content, "text/html")  # Attach HTML content
    email_message.send()


def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get('email')

        # Check if the email exists in AccountInformation
        try:
            account = AccountInformation.objects.get(email=email)
        except AccountInformation.DoesNotExist:
            return render(request, 'forgot_password.html', {
                'error': 'Email is not associated with any account.'
            })

        # Save email in session and reset the expiration
        request.session['email'] = email
        request.session.set_expiry(1800)  # Extend session expiry by 30 minutes

        # Generate a new OTP
        otp_data = generate_otp(email)
        if not otp_data["success"]:
            return render(request, 'forgot_password.html', {
                'error': otp_data["error"]
            })

        # Send the OTP to the user's email
        send_otp_to_email(email, otp_data["otp"])
        
        # Calculate remaining time for the countdown
        remaining_time = 1800  # 30 minutes in seconds

        return render(request, 'email_confirmation.html', {
            'success_message': 'OTP has been sent to your email.'
        })

    return render(request, 'forgot_password.html')


def resend_otp(request):
    email = request.session.get('email')  # Retrieve email from session
    if email:
        # Mark all unused OTPs as used
        OTPVerification.objects.filter(email=email, is_used=False).update(is_used=True)

        # Generate a new OTP
        otp_data = generate_otp(email)
        if otp_data.get("success"):
            otp = otp_data.get("otp")
            send_otp_to_email(email, otp)

            # Extend session expiration
            request.session.set_expiry(3600)  # Extend session expiry by 30 minutes

            # Render the email_confirmation.html with a success message
            return render(request, 'email_confirmation.html', {
                'success_message': 'OTP has been resent to your email.'
            })
        else:
            return render(request, 'email_confirmation.html', {
                'error': 'Failed to generate OTP. Please try again.'
            })
    else:
        return render(request, 'login.html', {
            'error': 'Session expired. Please log in again.'
        })





    
@csrf_exempt
def reset_password_view(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        account_id = request.session.get('account_id')

        if not account_id:
            return JsonResponse({"success": False, "error": "Session expired. Please try again."})

        if len(new_password) < 6:
            return JsonResponse({"success": False, "error": "Password must be at least 6 characters long."})

        if new_password != confirm_password:
            return JsonResponse({"success": False, "error": "Passwords do not match."})

        try:
            account = AccountInformation.objects.get(account_id=account_id)
            account.password = new_password  # Save plain text as per your requirement
            account.save()
            return JsonResponse({"success": True, "message": "Password updated successfully!"})
        except AccountInformation.DoesNotExist:
            return JsonResponse({"success": False, "error": "Account not found."})

    return JsonResponse({"success": False, "error": "Invalid request."})
