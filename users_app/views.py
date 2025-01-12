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
from bayanihire_app.models import AccountInformation, OTPVerification, VerificationToken
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth import logout
from django.utils.timezone import now, timedelta
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from django.shortcuts import get_object_or_404
from urllib.parse import urlparse, parse_qs, urlencode
import uuid
from django.db.models import F, Value
from django.db.models.functions import Coalesce
from functools import wraps
from django.views.decorators.cache import never_cache

def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        @never_cache 
        def _wrapped_view(request, *args, **kwargs):
            # Check if the user is logged in first
            if 'account_id' not in request.session:
                messages.error(request, "You must log in first.")
                return redirect('login')

            # Retrieve the account ID from the session
            account_id = request.session['account_id']

            try:
                # Retrieve the account from the database
                account_storage = AccountStorage.objects.get(account__account_id=account_id)

                # Check if the user's role is one of the allowed roles
                if account_storage.role not in allowed_roles:
                    # Clear the session and display a permission error
                    request.session.flush()
                    messages.error(request, "You do not have permission to access this page. You have been automatically logged out.")
                    return HttpResponseRedirect(reverse('login'))
            except AccountStorage.DoesNotExist:
                # Clear the session and inform the user their account is not found
                request.session.flush()
                messages.error(request, "Your account was not found or is no longer active.")
                return HttpResponseRedirect(reverse('login'))
            
            # If all checks pass, proceed to the view
            return view_func(request, *args, **kwargs)
        
        return _wrapped_view
    return decorator

def logout_view(request):
    logout(request)  # This clears all sessions and cookies related to this session
    response = redirect('login')
    response.delete_cookie('sessionid', path='/')  # Optional: Explicitly remove session cookie
    response['Cache-Control'] = 'no-store'  # Ensures pages are not cached by the browser
    return response

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
@role_required('interviewer') 
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

@role_required('interviewer') 
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

@role_required('interviewer') 
def interviewer_editfeedback(request):    
    return render(request, 'EditFeedback.html')


##ito
@role_required('interviewer') 
def interviewer_viewinfo(request, applicant_status_id):
    # Fetch the applicant using the provided applicant_status_id
    applicant = get_object_or_404(ListOfApplicantsWithStatusAndCredentials, applicant_status_id=applicant_status_id)

    # Ensure only qualified applicants can be accessed by the interviewer
    if applicant.applicant_status != "QUALIFIED":
        raise Http404("You do not have access to this applicant's files.")

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

    # Render the interviewer's template with context
    context = {
        'applicant': account_info,
        'job_details': job_details,
        'uploaded_files': uploaded_files,
        'submission_date': applicant.submission_date,
        'applicant_status': applicant.applicant_status,
        'applicant_status_id': applicant.applicant_status_id, 
        'interviewer_feedback_status': applicant.interviewer_feedback_status,
    }

    return render(request, 'ViewInfo.html', context)

#oks na to
@role_required('interviewer') 
def interviewer_feedback(request, applicant_status_id):
    account_id = request.session.get('account_id')
    if not account_id:
        return redirect('login')

    # Fetch the specific applicant using applicant_status_id
    applicant = get_object_or_404(ListOfApplicantsWithStatusAndCredentials, applicant_status_id=applicant_status_id)
    applicant_info = {
        'applicant_status_id': applicant.applicant_status_id,
        'first_name': applicant.account.first_name,
        'middle_name': applicant.account.middle_name,
        'last_name': applicant.account.last_name,
        'job_title': applicant.job.job_title,
        'interviewer_feedback_status': applicant.interviewer_feedback_status
    }

    if request.method == 'POST':
        status = request.POST.get('status')
        feedback = request.POST.get('feedback')

        # Update the applicant's status and feedback
        applicant.interviewer_feedback_status = status
        applicant.interviewer_feedback = feedback

        # Automatically update the applicant_status when the interview status indicates the interview is complete
        if status in ['PASSED', 'FAILED']:  # Assuming these are the statuses that imply interview completion
            applicant.applicant_status = 'PENDING FINAL APPROVAL'

        applicant.save()
        messages.success(request, "Feedback and status updated successfully.")
        return redirect('INTappointments')

    return render(request, 'Feedback.html', {'applicant': applicant_info})





# WEIN BAGO#
@role_required('interviewer') 
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

@role_required('interviewer') 
def interviewer_profile(request):        
    return render(request, 'Profile.html')
##################INTERVIEWER######################


###################APPLICANT############################
@role_required('applicant') 
def applicant_homepage(request):
    jobs = JobDetailsAndRequirements.objects.filter(job_status='ACTIVE')  # Fetch only active jobs
    context = {
        'jobs': jobs  # Pass the jobs to the template context
    }
    return render(request, 'Applicant_homepage.html', context)

@role_required('applicant') 
def applicant_jobreq(request, job_id):
    job_details = get_object_or_404(JobDetailsAndRequirements, job_id=job_id)

    # Check if the user has already applied for this job
    account_id = request.session.get('account_id')
    if not account_id:
        return JsonResponse({"error": "User must be logged in."}, status=403)

    already_applied = ListOfApplicantsWithStatusAndCredentials.objects.filter(
        job_id=job_id, account_id=account_id
    ).exists()

    # Pass the already_applied flag to the template
    context = {
        'job_details': job_details,
        'already_applied': already_applied,
    }

    return render(request, 'Applicant_JobReq.html', context)

@role_required('applicant') 
def applicant_fileupload(request, job_id):        
    uploaded_files_display = []

    if request.method == 'GET':
        context = {'job_id': job_id, 'uploaded_files_display': uploaded_files_display}
        return render(request, 'Applicant_fileupload.html', context)

    if request.method == 'POST':
        uploaded_files = request.FILES.getlist('files')
        max_file_size = 64 * 1024 * 1024  # 64MB

        allowed_file_types = ['application/pdf', 'image/jpeg', 'image/png']

        if not uploaded_files:
            return JsonResponse({"error": "No files selected."}, status=400)
        
        for uploaded_file in uploaded_files:
            if uploaded_file.size > max_file_size:
                return JsonResponse(
                    {"error": f"File '{uploaded_file.name}' exceeds the 64MB size limit."}, status=400
                )
            
            if uploaded_file.content_type not in allowed_file_types:
                return JsonResponse(
                    {"error": f"File '{uploaded_file.name}' is not a valid format. Only PDF, PNG, and JPEG are allowed."}, status=400
                )

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
        }

        success_url = reverse('homepage') + "?message=Successfully applied! Your application has been submitted.&type=success"
        return redirect(success_url)

    return JsonResponse({"error": "Invalid request method."}, status=405)



@role_required('applicant') 
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
            'job__job_id',
            'job__job_company'
        )
    )

    context = {
        'applications': applications,  # Pass the applications to the template
        'has_applications': applications.exists()  # Flag to check if applications exist
    }

    return render(request, 'Applicant_Applicationstatus.html', context)

@role_required('applicant') 
def applicant_viewfileupload(request, applicant_status_id):
    # Retrieve the application details using the applicant_status_id
    application = get_object_or_404(ListOfApplicantsWithStatusAndCredentials, applicant_status_id=applicant_status_id)

    # Fetch account information from the related model (assuming a ForeignKey relationship)
    applicant_account = application.account  # Replace `account` with the actual field name if different

    # Prepare to retrieve the uploaded files as binary
    uploaded_files = []

    # Split the file_metadata string into individual file names
    filenames = application.file_metadata.split(', ') if application.file_metadata else []  # Split by comma and space

    # Ensure you have the credentials data for each file
    if application.credentials and filenames:
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
        'applicant': {
            'full_name': f"{applicant_account.first_name} {applicant_account.middle_name} {applicant_account.last_name}",
            'age': applicant_account.age,
            'gender': applicant_account.gender,
            'mobile_number': applicant_account.mobile_number,
            'email': applicant_account.email,
            'address':  (
                f"{getattr(applicant_account, 'house_no', '')}, "
                f"{getattr(applicant_account, 'street_village', '')}, "
                f"{getattr(applicant_account, 'barangay', '')}, "
                f"{getattr(applicant_account, 'city_municipality', '')}, "
                f"{getattr(applicant_account, 'province', '')}, "
                f"{getattr(applicant_account, 'state', '')} "
                f"({getattr(applicant_account, 'zipcode', '')})"
            ).strip(', '),  # Remove trailing commas and spaces
        },
        'uploaded_files': uploaded_files,
    }

    return render(request, 'Applicant_Viewfileupload.html', context)

@role_required('applicant') 
def applicant_interviewdetails(request, applicant_status_id):
    # Fetch interview details for the given applicant
    applicant = get_object_or_404(ListOfApplicantsWithStatusAndCredentials, applicant_status_id=applicant_status_id)

    # Check if the applicant is qualified
    if applicant.applicant_status == "QUALIFIED":
        # Check if interview details exist for the qualified applicant
        if applicant.admin_message and applicant.applicant_schedule_date and applicant.location:
            # Include location data
            interview_details = {
                'interviewer_name': applicant.interview_applicant_id.interviewer_name if applicant.interview_applicant_id else "N/A",
                'schedule_date': applicant.applicant_schedule_date,
                'interview_message': applicant.admin_message,
                'location': applicant.location,
                'applicant_job_id': applicant.applicant_status_id

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

@role_required('applicant') 
def applicant_profile(request):
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
    return render(request, 'Applicant_profile.html', context)

###################APPLICANT############################
@role_required('applicant') 
def generate_pdf(request, applicant_status_id):
    # Ensure the user is logged in
    account_id = request.session.get('account_id')
    if not account_id:
        return HttpResponse("You must be logged in to generate a PDF.", status=403)
    
    user = get_object_or_404(AccountInformation, account_id=account_id)

    # Fetch the specific qualified job application
    application = get_object_or_404(
        ListOfApplicantsWithStatusAndCredentials,
        applicant_status_id=applicant_status_id,
        account=user,
        applicant_status="QUALIFIED"
    )

    # Fetch the related job and interviewer details
    job = application.job
    interview_instance = application.interview_applicant_id  # Fetch interview details if available

    # Prepare job details for the specific application
    job_details = [{
        'applicant_job_id': application.applicant_status_id,
        'job_title': job.job_title,
        'job_company': job.job_company,
        'job_date_published': job.job_date_published,
        'application_status': application.applicant_status,
        'submission_date': application.submission_date,
        'interviewer_name': interview_instance.interviewer_name if interview_instance else "N/A",
        'schedule_date': application.applicant_schedule_date if application.applicant_schedule_date else "N/A",
        'interview_message': application.admin_message if application.admin_message else "N/A",
        'location': application.location if application.location else "N/A",
    }]

    # Generate dynamic file name: "{last_name}_Application_{job_title}.pdf"
    file_name = f"{user.last_name or 'Applicant'}_Application.pdf"
    

    # Context for the template
    context = {
        'account_info': {
            'full_name': f"{user.first_name} {user.middle_name or ''} {user.last_name}".strip(),
            'email': user.email,
            'mobile_number': user.mobile_number,
            'birth_date': user.birth_date,
            'age': user.age,
            'gender': user.gender,
            'address': f"{user.house_no} {user.street_village}, {user.barangay}, {user.city_municipality}, "
                       f"{user.province}, {user.state}, {user.zipcode}".strip(),
        },
        'job_details': job_details,
    }

    # Render the template to HTML
    html = render_to_string('Generatepdf_Applicant.html', context)

    # Create a PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'
    pisa_status = pisa.CreatePDF(html, dest=response)

    # Check for PDF generation errors
    if pisa_status.err:
        return HttpResponse("There was an error generating the PDF.", status=500)

    return response



###################GENERATE PDF SYSTEM ############################
@role_required('admin') 
def generate_system_pdf(request):
    # Ensure the user is logged in
    account_id = request.session.get('account_id')
    if not account_id:
        return HttpResponse("You must be logged in to generate a PDF.", status=403)

    # Fetch the admin's account information
    admin = get_object_or_404(AccountInformation, account_id=account_id)

    # Collect data about users, jobs, and applicants
    users = AccountInformation.objects.all()
    jobs = JobDetailsAndRequirements.objects.all()
    applicants = ListOfApplicantsWithStatusAndCredentials.objects.select_related('job', 'account').all()
    account_storages = AccountStorage.objects.select_related('account').all()
 
    # Calculate user types and job statuses
    total_applicants = account_storages.filter(role='applicant').count()
    total_admins = account_storages.filter(role='admin').count()
    total_interviewers = account_storages.filter(role='interviewer').count()
    verified_users = users.filter(verified=True).count()
    unverified_users = users.filter(verified=False).count()
    active_accounts = account_storages.filter(account_status='active').count()
    deactivated_accounts = account_storages.filter(account_status='deactivated').count()
    new_accounts = account_storages.filter(account_status='new').count()

    # Job status counts
    jobs_active = jobs.filter(job_status='ACTIVE').count()
    jobs_closed = jobs.filter(job_status='CLOSED').count()

    # Applicant statuses
    applicants_under_review = ListOfApplicantsWithStatusAndCredentials.objects.filter(applicant_status='UNDER REVIEW').count()
    applicants_for_interview = ListOfApplicantsWithStatusAndCredentials.objects.filter(applicant_status='FOR INTERVIEW').count()
    applicants_failed_to_meet_requirements = ListOfApplicantsWithStatusAndCredentials.objects.filter(applicant_status='FAILED TO MEET REQUIREMENTS').count()
    applicants_incomplete = ListOfApplicantsWithStatusAndCredentials.objects.filter(applicant_status='INCOMPLETE').count()
    applicants_rejected = ListOfApplicantsWithStatusAndCredentials.objects.filter(applicant_status='REJECTED').count()
    applicants_qualified = ListOfApplicantsWithStatusAndCredentials.objects.filter(applicant_status='QUALIFIED').count()
    applicants_passed = ListOfApplicantsWithStatusAndCredentials.objects.filter(applicant_status='PASSED').count()
    applicants_failed = ListOfApplicantsWithStatusAndCredentials.objects.filter(applicant_status='FAILED').count()
    applicants_pending_final_approval = ListOfApplicantsWithStatusAndCredentials.objects.filter(applicant_status='PENDING FINAL APPROVAL').count()
    
    # Prepare data for the template
    context = {
        'date_generated': timezone.now().date(),
        'requested_by': f"{admin.first_name} {admin.middle_name} {admin.last_name} - {admin.username}",
        'total_users': users.count(),
        'total_applicants': total_applicants,
        'total_admins': total_admins,
        'total_interviewers': total_interviewers,
        'verified_users': verified_users,
        'unverified_users': unverified_users,
        'active_accounts': active_accounts,
        'deactivated_accounts': deactivated_accounts,
        'new_accounts': new_accounts,
        'jobs': jobs,
        'total_jobs': jobs.count(),
        'jobs_active': jobs_active,
        'jobs_closed': jobs_closed,
        'applicants': applicants,
        'applicants_under_review': applicants_under_review,
        'applicants_for_interview': applicants_for_interview,
        'applicants_failed_to_meet_requirements': applicants_failed_to_meet_requirements,
        'applicants_incomplete': applicants_incomplete,
        'applicants_rejected': applicants_rejected,
        'applicants_qualified': applicants_qualified,
        'applicants_passed': applicants_passed,
        'applicants_failed': applicants_failed,
        'applicants_pending_final_approval': applicants_pending_final_approval,
    }

    # Render the HTML template to a string
    html = render_to_string('ADMIN_GENERATEPDF.html', context)

    # Create a PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="System_Report.pdf"'

    # Generate PDF
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("There was an error generating the PDF.", status=500)

    return response



##########################Admin###############################################
logger = logging.getLogger(__name__)

@role_required('admin') 
def list_of_applicants(request):        
    search_query = request.GET.get('search', '').strip()
    sort_type = request.GET.get('sort_type', '')
    sort_order = request.GET.get('sort_order', 'asc')
    status_filter = request.GET.get('status', '')
    rows_param = request.GET.get('rows', '5')
    rows_per_page = max(min(int(rows_param), 10), 1) if rows_param.isdigit() else 5

    query = (
        Q(account__first_name__icontains=search_query) | 
        Q(account__middle_name__icontains=search_query) | 
        Q(account__last_name__icontains=search_query) | 
        Q(job__job_company__icontains=search_query) | 
        Q(job__job_title__icontains=search_query)
    )
    
    if search_query:
        applicants = ListOfApplicantsWithStatusAndCredentials.objects.filter(query)
    else:
        applicants = ListOfApplicantsWithStatusAndCredentials.objects.all()

    if status_filter:
        applicants = applicants.filter(applicant_status=status_filter)
    
    total_applicants_under_review = ListOfApplicantsWithStatusAndCredentials.objects.filter(applicant_status="UNDER REVIEW").count()

    # Handling sorting based on the type and order
    if sort_type:
        if 'name' in sort_type:
            base_sort_field = 'account__last_name' if 'name' in sort_type else sort_type
            direction = '-' if 'desc' in sort_type else ''
            applicants = applicants.order_by(direction + 'account__first_name', direction + 'account__middle_name', direction + 'account__last_name')
        elif 'job_company' in sort_type:
            direction = '-' if 'desc' in sort_type else ''
            applicants = applicants.order_by(direction + 'job__job_company')
        elif 'job_title' in sort_type:
            direction = '-' if 'desc' in sort_type else ''
            applicants = applicants.order_by(direction + 'job__job_title')
        elif 'submission_date' in sort_type:
            direction = '-' if 'desc' in sort_type else ''
            applicants = applicants.order_by(direction + 'submission_date')

    paginator = Paginator(applicants, rows_per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'applicant_data': [{
            'no': (page_obj.number - 1) * rows_per_page + idx + 1,
            'full_name': f"{a.account.first_name} {a.account.middle_name or ''} {a.account.last_name}",
            'company': a.job.job_company,
            'position_applied': a.job.job_title,
            'date_applied': a.submission_date.strftime("%Y-%m-%d"),  # Ensure dates are formatted nicely
            'status': a.applicant_status,
            'applicant_status_id': a.applicant_status_id,
        } for idx, a in enumerate(page_obj)],
        'total_applicants_under_review': total_applicants_under_review,
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_order': sort_order,
        'sort_type': sort_type,
        'status_filter': status_filter,
        'rows_per_page': rows_per_page,
    }
    return render(request, 'AdminView_1_Homepage_ListofApplicants.html', context)

@role_required('admin') 
def open_applicants(request, applicant_status_id):
    # Fetch the applicant using the provided applicant_status_id
    applicant = get_object_or_404(ListOfApplicantsWithStatusAndCredentials, applicant_status_id=applicant_status_id)

    # Store the current page as the "previous_page" in session
    if request.method == 'GET':
        referrer = request.META.get('HTTP_REFERER', '/list_of_applicants/')
        parsed_url = urlparse(referrer)
        base_url = parsed_url.path
        query_params = parse_qs(parsed_url.query)

        # Reconstruct the URL with query parameters
        reconstructed_url = f"{base_url}?{urlencode(query_params, doseq=True)}"
        request.session['previous_page'] = reconstructed_url

    if request.method == 'POST':
        applicant = get_object_or_404(ListOfApplicantsWithStatusAndCredentials, applicant_status_id=applicant_status_id)
        # Handle status update
        if applicant.applicant_status in ["FAILED", "PASSED"]:
            # Redirect back to the stored previous page with an error message
            previous_page = request.session.get('previous_page')
            return redirect(f"{previous_page}&message=This applicant has already been interviewed and cannot be updated further.&type=error")
        if applicant.applicant_status in ["QUALIFIED", "PENDING FINAL APPROVAL"]:
            # Redirect back to the stored previous page with an error message
            previous_page = request.session.get('previous_page')
            return redirect(f"{previous_page}&message=This applicant is currently undergoing the interview process and cannot be updated at this time.&type=error")


        new_status = request.POST.get('new_status')
        applicant.applicant_status = new_status
        applicant.save()

        # Redirect back to the stored previous page with a success message
        previous_page = request.session.get('previous_page')
        return redirect(f"{previous_page}&message=Applicant status updated successfully.&type=success")

    # Handle GET: Display applicant details
    account_info = applicant.account
    job_details = applicant.job

    # Prepare the list of uploaded files (from comma-separated metadata)
    uploaded_files = []
    filenames = applicant.file_metadata.split(", ") if applicant.file_metadata else []

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

@role_required('admin') 
def viewing_files(request, file_name):        
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

@role_required('admin') 
def list_of_jobs(request):
    search_query = request.GET.get('search', '').strip()
    sort_type = request.GET.get('sort', '')  # Default sort by job title ascending
    sort_order = 'desc' if 'desc' in sort_type else 'asc'  # Ensure proper sort order
    job_status = request.GET.get('status', '')  # Retrieve job status filter
    rows_param = request.GET.get('rows', '5')  # Default rows per page is 5
    rows_per_page = max(min(int(rows_param), 10), 1) if rows_param.isdigit() else 5

    # Build query for job title or company search
    query = Q(job_title__icontains=search_query) | Q(job_company__icontains=search_query)

    if job_status:
        query &= Q(job_status__iexact=job_status)  # Apply status filter

    jobs = JobDetailsAndRequirements.objects.filter(query)

    # Apply sorting based on the type
    direction = '-' if sort_order == 'desc' else ''
    if 'title' in sort_type:
        jobs = jobs.order_by(f"{direction}job_title")
    elif 'company' in sort_type:
        jobs = jobs.order_by(f"{direction}job_company")
    elif 'date' in sort_type:
        jobs = jobs.order_by(f"{direction}job_date_published")

    # Setup pagination
    paginator = Paginator(jobs, rows_per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'jobs': page_obj,
        'active_jobs_count': JobDetailsAndRequirements.objects.filter(job_status="ACTIVE").count(),
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_type': sort_type,
        'job_status': job_status,
        'rows_per_page': rows_per_page,
        'start_index': (page_obj.number - 1) * rows_per_page + 1,
    }

    return render(request, 'AdminView_2_ListofJobs.html', context)

@role_required('admin') 
def edit_job_details(request, job_id):
    job = get_object_or_404(JobDetailsAndRequirements, pk=job_id)

    # Store the current page as the "previous_page" in session
    if request.method == 'GET':
        referrer = request.META.get('HTTP_REFERER', '/list_of_jobs/')
        parsed_url = urlparse(referrer)
        base_url = parsed_url.path
        query_params = parse_qs(parsed_url.query)

        # Reconstruct the URL with query parameters
        reconstructed_url = f"{base_url}?{urlencode(query_params, doseq=True)}"
        request.session['previous_page'] = reconstructed_url

    if request.method == 'POST':
        # Update fields with form data
        try:
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

            # Redirect back to the stored previous page with a success message
            previous_page = request.session.get('previous_page')
            return redirect(f"{previous_page}&message=Job details updated successfully.&type=success")

        except Exception as e:
            # Redirect back to the stored previous page with an error message
            previous_page = request.session.get('previous_page')
            return redirect(f"{previous_page}&message=Error updating job details: {str(e)}.&type=error")

    # Format the date for display, default to today if no date is set
    job_date = job.job_date_published or date.today()
    job_date = job_date.strftime("%Y-%m-%d")  # Format as YYYY-MM-DD for HTML input

    return render(request, 'AdminView_2_1_EditJobDetails.html', {
        'job': job,
        'job_date': job_date,
    })

@role_required('admin') 
def create_job_details(request):
    # Store the current page as the "previous_page" in session
    if request.method == 'GET':
        referrer = request.META.get('HTTP_REFERER', '/list_of_jobs/')
        parsed_url = urlparse(referrer)
        base_url = parsed_url.path
        query_params = parse_qs(parsed_url.query)

        # Reconstruct the URL with query parameters
        reconstructed_url = f"{base_url}?{urlencode(query_params, doseq=True)}"
        request.session['previous_page'] = reconstructed_url

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
        if not account_id:
            return redirect('login')  # Redirect to login if no user is logged in

        account = get_object_or_404(AccountInformation, account_id=account_id)

        # Validate required fields
        if not (status and job_title and company and job_description and job_requirements):
            previous_page = request.session.get('previous_page')
            return redirect(f"{previous_page}&message=All fields are required.&type=error")

        try:
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

            # Redirect back to the stored previous page with a success message
            previous_page = request.session.get('previous_page')
            return redirect(f"{previous_page}&message=Job created successfully.&type=success")

        except Exception as e:
            # Redirect back to the stored previous page with an error message
            previous_page = request.session.get('previous_page')
            return redirect(f"{previous_page}&message=Error creating job: {str(e)}.&type=error")

    # Process GET request
    today_date = date.today().strftime("%Y-%m-%d")  # Format today's date as YYYY-MM-DD
    return render(request, 'AdminView_2_2_CreateJobDetails.html', {'today_date': today_date})

@role_required('admin') 
def qualification(request):        
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
    
@role_required('admin') 
def send_schedule(request):
    # Fetch all applicants who are set for interview
    applicants = ListOfApplicantsWithStatusAndCredentials.objects.filter(
        applicant_status='FOR INTERVIEW'
    ).select_related('account', 'job', 'interview_applicant_id')

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
        # Fetch form data
        interviewer_name = request.POST.get('interviewer_name')
        selected_schedule_date = request.POST.get('selected_schedule_date')
        interview_message = request.POST.get('interview_message')
        location = request.POST.get('interview_location')

        # Debugging logs
        print("Form Data Received:")
        print(f"Interviewer Name: {interviewer_name}")
        print(f"Schedule Date: {selected_schedule_date}")
        print(f"Interview Message: {interview_message}")
        print(f"Location: {location}")

        # Validate form inputs
        if not (interviewer_name and selected_schedule_date and location):
            print("Validation Failed: Missing required fields.")
            return render(request, 'AdminView_3_1_Send.html', {
                'applicants': applicant_data,
                'interviewer_name': interviewer_name,
                'schedule_date': selected_schedule_date,
                'interview_message': interview_message,
                'location': location,
                'error': "All fields, including the location, are required.",
            })

        # Process each applicant and save details
        for applicant in applicants:
            try:
                print(f"Processing Applicant ID: {applicant.applicant_status_id}")

                # Update location and interview details in the applicant's record
                applicant.admin_message = interview_message
                applicant.applicant_schedule_date = selected_schedule_date
                applicant.location = location  # Save textual location only
                applicant.save()
                print(f"Updated Applicant Details for Applicant ID: {applicant.applicant_status_id}")

            except Exception as e:
                print(f"Error processing Applicant ID {applicant.applicant_status_id}: {e}")

        print("All data processed successfully.")
        return render(request, 'AdminView_3_1_Send.html', {
            'applicants': applicant_data,
            'interviewer_name': interviewer_name,
            'schedule_date': selected_schedule_date,
            'interview_message': interview_message,
            'location': location,
            'success': "Interview details have been successfully saved.",
        })

    # Render the page with initial applicant data for GET requests
    return render(request, 'AdminView_3_1_Send.html', {
        'applicants': applicant_data
    })


@role_required('admin') 
def confirm_send_schedule(request):
    if request.method == "POST":
        # Retrieve data from POST request
        interviewer_name = request.POST.get('interviewer_name')
        schedule_date = request.POST.get('schedule_date')
        interview_message = request.POST.get('interview_message')
        location = request.POST.get('interview_location')  # Include location now
        applicant_ids = request.POST.getlist('applicant_ids[]')

        # Debugging: Log received data
        print(f"Confirm Schedule -> Interviewer: {interviewer_name}, Date: {schedule_date}, Location: {location}, Applicants: {applicant_ids}")

        # Ensure interview instance exists
        interview_instance = InterviewStorage.objects.filter(
            interviewer_name=interviewer_name,
            interview_schedule_date=schedule_date
        ).first()
        if not interview_instance:
            print("Error: No matching interview instance found.")
            return redirect('send_schedule')  # Handle error gracefully

        with transaction.atomic():
            for applicant_id in applicant_ids:
                # Retrieve and update applicant
                applicant = get_object_or_404(ListOfApplicantsWithStatusAndCredentials, applicant_status_id=applicant_id)
                applicant.interview_applicant_id = interview_instance
                applicant.applicant_schedule_date = schedule_date
                applicant.admin_message = interview_message
                applicant.location = location  # Save the textual location
                applicant.applicant_status = 'QUALIFIED'
                applicant.save()
                print(f"Updated Applicant ID {applicant_id} with Location: {location}")

        return redirect('list_of_applicants')  # Redirect to confirmation or success page

    return redirect('send_schedule')  # Redirect if method is not POST

@role_required('admin') 
def open_schedule_list(request):
    # Extract parameters
    interviewer_name = request.GET.get('interviewer', None)
    search_query = request.GET.get('search', '').strip()
    sort_type = request.GET.get('sort_type', '')
    rows_param = request.GET.get('rows', '5')
    rows_per_page = max(min(int(rows_param), 10), 1) if rows_param.isdigit() else 5

    # Annotate each applicant with the interviewer's name from the related InterviewStorage
    applicants = ListOfApplicantsWithStatusAndCredentials.objects.annotate(
        interviewer_name=Coalesce(F('interview_applicant_id__interviewer_name'), Value('Interviewer Still Pending'))
    )

    # Apply filtering
    if interviewer_name:
        applicants = applicants.filter(interviewer_name__icontains=interviewer_name)

    if search_query:
        applicants = applicants.filter(
            Q(account__first_name__icontains=search_query) |
            Q(account__last_name__icontains=search_query)
        )

    # Sorting logic
    if sort_type == 'name_asc':
        applicants = applicants.order_by('account__first_name', 'account__last_name')
    elif sort_type == 'name_desc':
        applicants = applicants.order_by('-account__first_name', '-account__last_name')
    elif sort_type == 'interviewer_asc':
        applicants = applicants.order_by('interviewer_name')
    elif sort_type == 'interviewer_desc':
        applicants = applicants.order_by('-interviewer_name')
    elif sort_type == 'date_asc':
        applicants = applicants.order_by('applicant_schedule_date')
    elif sort_type == 'date_desc':
        applicants = applicants.order_by('-applicant_schedule_date')

    # Pagination setup
    paginator = Paginator(applicants, rows_per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Fetch unique interviewer names for the dropdown
    interviewers = InterviewStorage.objects.values('interviewer_name').distinct()

    # Context data
    context = {
        'applicants': page_obj,
        'interviewers': interviewers,
        'search_query': search_query,
        'interviewer_name': interviewer_name,
        'sort_type': sort_type,
        'rows_per_page': rows_per_page,
        'page_obj': page_obj,
    }

    return render(request, 'AdminView_3_2_OpenScheduleList.html', context)

@role_required('admin') 
def schedule(request):
    today = date.today()
    search_query_interviewer = request.GET.get('search_interviewer', '').strip()
    sort_type = request.GET.get('sort_type', '')
    sort_order = request.GET.get('sort_order', 'asc')
    rows_interviewer = request.GET.get('rows_interviewer', '5')
    page_number_interviewer = request.GET.get('page_interviewer', '1')

    interviewers = AccountStorage.objects.filter(role='interviewer').select_related('account')
    if search_query_interviewer:
        interviewers = interviewers.filter(
            Q(account__first_name__icontains=search_query_interviewer) |
            Q(account__middle_name__icontains=search_query_interviewer) |
            Q(account__last_name__icontains=search_query_interviewer)
        )

    # Corrected sorting logic: Sorting by both first and last names
    if sort_type:
        if 'name_asc' == sort_type:
            interviewers = interviewers.order_by('account__first_name', 'account__last_name')
        elif 'name_desc' == sort_type:
            interviewers = interviewers.order_by('-account__first_name', '-account__last_name')

    if request.method == "POST":
        selected_interviewer_name = request.POST.get('selected_interviewer')
        interview_date = request.POST.get('interview_date')
        if interview_date:
            interview_date_obj = date.fromisoformat(interview_date)
            if interview_date_obj <= today:
                query_params = {
                    'search_interviewer': search_query_interviewer,
                    'sort_type': sort_type,
                    'sort_order': sort_order,
                    'rows_interviewer': rows_interviewer,
                    'page_interviewer': page_number_interviewer,
                    'message': 'The selected date must be in the future.',
                    'type': 'error'
                }
                url_params = urlencode(query_params)
                url = f"{reverse('schedule')}?{url_params}"
                return HttpResponseRedirect(url)
        
        selected_interviewer = interviewers.filter(
            account__first_name__icontains=selected_interviewer_name.split()[0],
            account__last_name__icontains=selected_interviewer_name.split()[-1]
        ).first()

        if selected_interviewer:
            is_booked = InterviewStorage.objects.filter(
                account=selected_interviewer.account,
                interview_schedule_date=interview_date_obj
            ).exists()
            if is_booked:
                return redirect(f"{reverse('schedule')}?message=The date is already set for that interviewer.&type=error")

        if selected_interviewer:
            InterviewStorage.objects.create(
                account=selected_interviewer.account,
                role=selected_interviewer,
                interview_schedule_date=interview_date_obj,
                interviewer_name=selected_interviewer_name
            )
            return redirect(f"{reverse('view_schedule')}?message=Interview scheduled successfully.&type=success")
        else:
            return redirect(f"{reverse('view_schedule')}?message=Selected interviewer not found.&type=error")

    rows_interviewer = int(request.GET.get('rows_interviewer', 5))
    page_number_interviewer = request.GET.get('page_interviewer', 1)
    interviewer_paginator = Paginator(interviewers, rows_interviewer)
    page_obj_interviewer = interviewer_paginator.get_page(page_number_interviewer)

    context = {
        'interviewer_names': page_obj_interviewer,
        'search_query_interviewer': search_query_interviewer,
        'rows_interviewer': rows_interviewer,
        'page_obj_interviewer': page_obj_interviewer,
        'sort_type': sort_type,
        'sort_order': sort_order,
    }
    return render(request, 'AdminView_4_Schedule.html', context)

@role_required('admin') 
def view_schedule(request):
    search_query_schedule = request.GET.get('search_schedule', '').strip()
    sort_type = request.GET.get('sort_type', '')
    rows_schedule = request.GET.get('rows_schedule', 5)
    rows_schedule = max(min(int(rows_schedule), 10), 1)  # Ensure valid integer between 1 and 10

    query = Q(account__first_name__icontains=search_query_schedule) | \
            Q(account__last_name__icontains=search_query_schedule)

    interview_data = InterviewStorage.objects.filter(query).select_related('account').order_by(
        '-account__last_name' if sort_type == 'name_desc' else
        'account__last_name' if sort_type == 'name_asc' else
        '-interview_schedule_date' if sort_type == 'date_desc' else
        'interview_schedule_date'
    ).values('account__first_name', 'account__middle_name', 'account__last_name', 'interview_schedule_date')

    formatted_interview_data = [
        {
            "name": f"{entry['account__first_name'] or ''} {entry['account__middle_name'] or ''} {entry['account__last_name'] or ''}".strip(),
            "date": entry['interview_schedule_date']
        }
        for entry in interview_data
    ]

    paginator = Paginator(formatted_interview_data, rows_schedule)
    page_number = request.GET.get('page_schedule', 1)
    page_obj_schedule = paginator.get_page(page_number)

    context = {
        'formatted_interview_data': page_obj_schedule,
        'page_obj_schedule': page_obj_schedule,
        'search_query_schedule': search_query_schedule,
        'rows_schedule': rows_schedule,
        'sort_type': sort_type,
    }
    return render(request, 'AdminView_4_1_ViewSchedule.html', context)


@role_required('admin') 
def feedback(request):
    search_query = request.GET.get('search', '').strip()
    sort_type = request.GET.get('sort_name', '')
    status_filter = request.GET.get('status_filter', '')
    rows_param = request.GET.get('rows', '5')
    rows_per_page = max(min(int(rows_param), 10), 1) if rows_param.isdigit() else 5

    applicants = ListOfApplicantsWithStatusAndCredentials.objects.select_related('account', 'job') \
        .exclude(interviewer_feedback_status__isnull=True) \
        .exclude(interviewer_feedback_status='') \
        .annotate(full_name=Concat('account__first_name', Value(' '), 'account__middle_name', Value(' '), 'account__last_name'))


    if search_query:
        applicants = applicants.filter(
            Q(full_name__icontains=search_query) |
            Q(job__job_title__icontains=search_query) |
            Q(job__job_company__icontains=search_query)
        )

    if status_filter:
        if status_filter in ["Interview Status Passed", "Interview Status Failed"]:
            applicants = applicants.filter(interviewer_feedback_status=status_filter.split()[-1])
        else:
            applicants = applicants.filter(applicant_status=status_filter.split()[-1])

    if sort_type:
        direction = '-' if 'desc' in sort_type else ''
        if 'name' in sort_type:
            sort_fields = [direction + 'account__first_name', direction + 'account__middle_name', direction + 'account__last_name']
        elif 'company' in sort_type:
            sort_fields = [direction + 'job__job_company']
        elif 'position' in sort_type:
            sort_fields = [direction + 'job__job_title']
        else:
            sort_fields = [direction + 'submission_date']
            
        applicants = applicants.order_by(*sort_fields)

    paginator = Paginator(applicants, rows_per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'applicants': page_obj,
        'search_query': search_query,
        'sort_type': sort_type,
        'status_filter': status_filter,
        'rows_per_page': rows_per_page,
        'page_obj': page_obj,
    }
    return render(request, 'AdminView_5_Feedback.html', context)

@role_required('admin') 
def view_feedback(request, applicant_status_id):
    applicant = get_object_or_404(ListOfApplicantsWithStatusAndCredentials, pk=applicant_status_id)
       
    if request.method == 'GET':
        if not applicant.applicant_status:
            applicant.applicant_status = "PASSED"
            applicant.save()
        referrer = request.META.get('HTTP_REFERER', '/admin_feedback/')
        parsed_url = urlparse(referrer)
        base_url = parsed_url.path
        query_params = parse_qs(parsed_url.query)

        # Reconstruct the URL with query parameters
        reconstructed_url = f"{base_url}?{urlencode(query_params, doseq=True)}"
        request.session['previous_page'] = reconstructed_url

    if request.method == "POST":
        new_status = request.POST.get('applicant_status')
        if new_status:
            applicant.applicant_status = new_status
            applicant.save()
            previous_page = request.session.get('previous_page')
            return redirect(f"{previous_page}&message=Applicant status successfully updated.&type=success")


    # For GET requests or initial form rendering
    interviewer_name = applicant.interview_applicant_id.interviewer_name if applicant.interview_applicant_id else "No interviewer assigned"
    context = {
        'interviewer_name': interviewer_name,
        'applicant_name': f"{applicant.account.first_name} {applicant.account.last_name}",
        'interview_status': applicant.interviewer_feedback_status,
        'interview_feedback': applicant.interviewer_feedback,
        'applicant_status': applicant.applicant_status, 
        'applicant_status_id': applicant_status_id  # Needed to build the form action URL
    }
    
    return render(request, 'AdminView_5_1_ViewFeedback.html', context)


@role_required('admin') 
def adminprofile(request):        
    # Assuming the user's ID is stored in session
    account_id = request.session.get('account_id')
    user = get_object_or_404(AccountInformation, account_id=account_id)

    # For example, get the latest or a specific logic-based status ID
    applicant_status = ListOfApplicantsWithStatusAndCredentials.objects.filter(
        account_id=account_id
    ).order_by('-submission_date').first()

    # Use a fallback if no applicant_status is found
    applicant_status_id = applicant_status.applicant_status_id if applicant_status else None

    
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
        'email': user.email,
        'applicant_status_id': applicant_status_id  # Dynamically set the ID
    }
    return render(request, 'AdminView_6_Profile.html', context)


@role_required('admin') 
def add_accounts(request):
    if request.method == 'GET':
        referrer = request.META.get('HTTP_REFERER', '/list_of_applicants/')
        parsed_url = urlparse(referrer)
        base_url = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        reconstructed_url = f"{base_url}?{urlencode(query_params, doseq=True)}"
        request.session['previous_page'] = reconstructed_url

    if request.method == 'POST':
        try:
            # Get the form data
            role = request.POST.get('role', '').strip().lower()
            birthday = request.POST.get('birthday', '').strip()
            gender = request.POST.get('gender', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            middle_name = request.POST.get('middle_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()

            # Initialize error dictionary
            errors = {}

            # Validate age
            if birthday:
                birth_date = datetime.strptime(birthday, "%Y-%m-%d")
                today = datetime.today()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                if age < 18:
                    errors['birthday_error'] = "Users must be at least 18 years old."
                if age > 65:
                    errors['birthday_error'] = "Users must not be older than 65 years."
            else:
                errors['birthday_error'] = "Birthday is required."

            # Validate names
            if len(first_name) < 2 or not first_name.replace(" ", "").isalpha():
                errors['first_name_error'] = "must be at 2+ characters long and contain only alphabetic characters."
            if len(last_name) < 2 or not last_name.replace(" ", "").isalpha():
                errors['last_name_error'] = "must be at least 2+ characters long and contain only alphabetic characters."
            if len(middle_name) < 2 or not (middle_name.replace(" ", "").isalpha() or middle_name == 'N/A'):
                errors['middle_name_error'] = "must be at least 2+ characters long and contain only alphabetic characters or 'N/A'."

            # Validate email
            if AccountInformation.objects.filter(email=email).exists():
                errors['email_error'] = "An account with this email already exists."
            if not email:
                errors['email_error'] = "Email is required."

            # Check if there are errors
            if errors:
                return render(request, 'AdminView_6_2_AddAccounts.html', {
                    "role": role,
                    "gender": gender,
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,
                    "email": email,
                    "birthday": birthday,
                    **errors  # Pass all error messages to the template
                })

            # Generate default username and password
            # Function to generate a unique username
            def generate_unique_username(base_name):
                while True:
                    random_number = random.randint(10, 99)  # Generate two random digits
                    username = f"{base_name.lower().replace(' ', '')}{random_number}@bynhr.com"
                    if not AccountInformation.objects.filter(username=username).exists():
                        return username

            # Generate unique username
            base_name = first_name  # Use the first name as the base
            username = generate_unique_username(base_name)

            # Generate password
            password = last_name.lower().replace(" ", "")  # Use the last name as the default password

            # Save to AccountInformation
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
            account_info.save()

            # Save to AccountStorage
            account_storage = AccountStorage(
                account=account_info,
                role=role,
                account_status='new'  # Default status
            )
            account_storage.save()
            
            # Generate a unique verification token
            token = uuid.uuid4()
            VerificationToken.objects.create(account=account_info, token=token)

            # Send the verification email
            send_verification_email(account_info, token)

            # Success message and redirect
            previous_page = request.session.get('previous_page', '/list_of_applicants/')
            messages.success(request, f"Account created successfully with username: {username}")
            return redirect(f"{previous_page}&message=Please Check your Email Address for verification&type=success")

        except Exception as e:
            # Handle errors and log them if needed
            return render(request, 'AdminView_6_2_AddAccounts.html', {
                "error": f"An error occurred: {e}"
            })

    # Render the form for GET request
    return render(request, 'AdminView_6_2_AddAccounts.html', {})

@role_required('admin') 
def manage_accounts(request):
    # Fetch search, sort, and rows parameters from GET
    search_query = request.GET.get('search', '').strip()
    sort_order = request.GET.get('sort', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    rows_param = request.GET.get('rows', '5')

    base_url = request.build_absolute_uri('/manage_accounts/')
    query_params = request.GET.dict() 
        
    # Set rows per page with a default of 5
    rows_per_page = max(min(int(rows_param), 15), 1) if rows_param.isdigit() else 5

    # Filter accounts based on search query
    accounts = AccountStorage.objects.all()
    if search_query:
        accounts = accounts.filter(account__username__icontains=search_query)

    # Apply role and status filters
    if role_filter:
        accounts = accounts.filter(role__icontains=role_filter)
    if status_filter:
        accounts = accounts.filter(account_status__iexact=status_filter)

    # Sort accounts based on sort order
    if sort_order == 'desc':
        accounts = accounts.order_by('-account__username')
    elif sort_order == 'asc':
        accounts = accounts.order_by('account__username')

    if request.method == "POST":
        action = request.POST.get('action')
        role_id = int(request.POST.get('role_id'))
        account_storage = AccountStorage.objects.get(role_id=role_id)

        # Update the account status based on the action
        if action == 'deactivate' and account_storage.account_status == 'active':
            account_storage.account_status = 'deactivated'
            account_storage.save()
            query_params.update({'message': 'This account has been deactivated.', 'type': 'error'})
            return redirect(f"{base_url}?{urlencode(query_params)}")

        elif action == 'reactivate' and account_storage.account_status == 'deactivated':
            account_storage.account_status = 'active'
            account_storage.save()
            query_params.update({'message': 'This account has been deactivated.', 'type': 'success'})
            return redirect(f"{base_url}?{urlencode(query_params)}")
        elif account_storage.account_status == 'active':
            query_params.update({'message': 'This account is already active.', 'type': 'error'})
            return redirect(f"{base_url}?{urlencode(query_params)}")

    # Pagination
    paginator = Paginator(accounts, rows_per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_order': sort_order,
        'rows_param': rows_param,
        'role_filter': role_filter,
        'status_filter': status_filter,
    }
    return render(request, 'AdminView_6_1_manage_accounts.html', context)




###########################ADMIN RETRIEVAL####################################

#WEIN BAGO DAGDAG 11-11-2024
from django.contrib import messages


@role_required('interviewer') 
def interviewer_editfeedback(request, applicant_status_id):        
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

@role_required('interviewer') 
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

@role_required('interviewer') 
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

@role_required('interviewer') 
def interviewer_profile(request):  
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
def login(request):
    if request.method == 'POST':
        username = request.POST.get('username').strip()
        password = request.POST.get('password').strip()
        
        try:
            # Retrieve the account using the username and password
            account = AccountInformation.objects.get(username=username, password=password)
            print("Account found:", account)  # Debugging statement to check retrieved account

            # Check if the account is verified
            if not account.verified:
                return render(request, 'login.html', {"message": "Account not verified. Please check your email for verification."})

            # Retrieve account storage details (if applicable)
            account_storage = AccountStorage.objects.filter(account=account).first()
            print("Account Storage found:", account_storage)  # Debugging statement to check storage

            if account_storage:
                if account_storage.account_status == 'new':
                    request.session['account_id'] = account.account_id
                    return redirect('Security')

                elif account_storage.account_status == 'deactivated':
                    return render(request, 'login.html', {"message": "Account is deactivated. Please contact support."})

                # Redirect based on role
                request.session['account_id'] = account.account_id
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
            # If username or password does not match, show error message
            return render(request, 'login.html', {"message": "Incorrect username or password."})

    return render(request, 'login.html')


def Registration(request):
    if request.method == 'POST':
        form = AccountInformationForm(request.POST)
        if form.is_valid():
            # Save the AccountInformation instance without committing
            account_info = form.save(commit=False)
            account_info.verified = False  # Initially set as not verified
            account_info.save()  # Save the account information

            # Create the corresponding AccountStorage entry
            AccountStorage.objects.create(
                account=account_info,  # Link to the account
                role='applicant',  # Set default role as 'applicant'
                account_status='active'  # Set default account status as 'active'
            )

            # Generate a unique verification token
            token = uuid.uuid4()
            VerificationToken.objects.create(account=account_info, token=token)

            # Send the verification email
            send_verification_email(account_info, token)

            # Add a success message
            messages.success(request, "A verification email has been sent. Please verify your email.")
            return redirect('login')
    else:
        form = AccountInformationForm()

    return render(request, 'registration.html', {'form': form})

##verify email
def verify_email(request, token):
    try:
        verification_token = VerificationToken.objects.get(token=token)

        if verification_token.is_expired():  # Check if the token is expired
            return HttpResponse("This verification link has expired.", status=400)

        account = verification_token.account
        account.verified = True  # Mark the account as verified
        account.save()

        # Delete the token after successful verification
        verification_token.delete()

        # Query AccountStorage by account ID
        try:
            account_storage = AccountStorage.objects.get(account_id=account.account_id)

            # Debug: Print role information
            print(f"Account role for account ID {account.account_id}: {account_storage.role}")

            # Validate role and send appropriate success email
            if account_storage.role and account_storage.role.lower() in ['admin', 'interviewer']:
                send_success_email_2(account)  # Admin/interviewer email
            else:
                send_success_email(account)  # Applicant email
        except AccountStorage.DoesNotExist:
            print(f"No AccountStorage found for account ID: {account.account_id}")
            return HttpResponse("Account role information is missing.", status=400)    

        # Redirect to a success page or login page
        return redirect('login')
    except VerificationToken.DoesNotExist:
        return HttpResponse("Invalid verification link.", status=400)

def send_verification_email(account, token):
    verification_link = f"{settings.BASE_URL}/verify-email/{token}/"
    subject = "Verify Your Email - BayaniHire"
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; text-align: center; margin: 20px; padding: 20px; background-color: #FFFFFF; border: 1px solid #ddd; border-radius: 10px;">
        <div>
            <h1 style="color: #5c332e;">BayaniHire</h1>
            <p style="color: #000000; margin-bottom: 15px;">Thanks for signing up, {account.first_name}!</p>
            <p style="color: #000000; margin-bottom: 15px;">We're excited to have you get started.</p>
            <p style="color: #000000; margin-bottom: 15px;">First, you need to verify your account. Just press the button below.</p>
            <a href="{verification_link}" style="background-color: #5c332e; color: #ffffff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px; margin-bottom: 15px;">
                Verify Email Now
            </a>
            <p style="color: #000000; margin-top: 20px; margin-bottom: 15px;">If you didn't create this account, please ignore this email.</p>
        </div>
    </body>
    </html>
    """


    email_message = EmailMultiAlternatives(
        subject=subject,
        body=f"Please verify your email by clicking the following link: {verification_link}",  # Fallback plain text
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[account.email],
    )
    email_message.attach_alternative(html_content, "text/html")
    email_message.send()

def send_success_email(account):
    subject = "Welcome to BayaniHire - Account Successfully Created!"
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; text-align: center; margin: 20px; padding: 20px; background-color: #FFFFFF; border: 1px solid #ddd; border-radius: 10px;">
        <div>
            <h1 style="color: #5c332e;">BayaniHire</h1>
            <p style="color: #000000; margin-bottom: 15px;">Congratulations, {account.first_name}!</p>
            <p style="color: #000000; margin-bottom: 15px;">Your account has been successfully created and verified.</p>
            <p style="color: #000000; margin-bottom: 15px;">You can now log in using the following username:</p>
            <p style="font-size: 18px; font-weight: bold; color: #5c332e; margin-bottom: 15px;">{account.username}</p>
            <p style="color: #000000; margin-bottom: 15px;">Use your account to find job opportunities and explore our platform. We’re excited to have you onboard!</p>
            <p style="color: #000000; margin-bottom: 15px;">If you have any questions, feel free to contact our support team.</p>
            <p style="color: #000000; margin-top: 20px; margin-bottom: 15px; font-weight: bold;">Happy job hunting!</p>
        </div>
    </body>
    </html>
    """

    email_message = EmailMultiAlternatives(
        subject=subject,
        body=f"Congratulations {account.first_name}, your account has been verified! You can now log in using your username: {account.username}.",  # Fallback plain text
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[account.email],
    )
    email_message.attach_alternative(html_content, "text/html")
    email_message.send()

def send_success_email_2(account):
    try:
        # Query AccountStorage to get the role
        account_storage = AccountStorage.objects.get(account_id=account.account_id)

        # Prepare email content
        subject = "Welcome to BayaniHire - Account Successfully Created!"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; text-align: center; margin: 20px; padding: 20px; background-color: #FFFFFF; border: 1px solid #ddd; border-radius: 10px;">
            <div>
                <h1 style="color: #5c332e;">BayaniHire</h1>
                <p style="color: #000000; margin-bottom: 15px;">Welcome, {account.first_name}!</p>
                <p style="color: #000000; margin-bottom: 15px;">Your account as an <strong>{account_storage.role.capitalize()}</strong> has been successfully verified.</p>
                <p style="color: #000000; margin-bottom: 15px;">You can now log in to the system using the following:</p>
                <p style="font-size: 18px; font-weight: bold; color: #000000; margin-bottom: 15px;">
                    username: <span style="color: #ff0000;">{account.username}</span>
                </p>
                <p style="font-size: 18px; font-weight: bold; color: #000000; margin-bottom: 15px;">
                    password: <span style="color: #ff0000;">{account.password}</span>
                </p>
                <p style="color: #000000; margin-bottom: 15px;">
                    <strong>Please ensure you change your password upon logging in for the first time.</strong>
                    If you have any questions, feel free to contact our support team.
                </p>
                <p style="color: #000000; margin-top: 20px; margin-bottom: 15px; font-weight: bold;">We are glad to have you on board!</p>
            </div>
        </body>
        </html>
        """

        # Send the email
        email_message = EmailMultiAlternatives(
            subject=subject,
            body=f"Congratulations {account.first_name}, your account has been verified! You can now log in using your username: {account.username}.",  # Fallback plain text
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[account.email],
        )
        email_message.attach_alternative(html_content, "text/html")
        email_message.send()

    except AccountStorage.DoesNotExist:
        print(f"No AccountStorage found for account ID: {account.account_id}")
        raise Exception("Account role information is missing.")  # Raise an exception to debug further
    except Exception as e:
        print(f"Error sending email: {e}")
        raise

    
def change_password(request):
    # Only allow POST requests and check if account_id exists in the session
    if request.method == 'POST' and 'account_id' in request.session:
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        # Fetch the account by account_id stored in the session
        account_id = request.session['account_id']
        account = AccountInformation.objects.get(account_id=account_id)

        # Validate that the new password is at least 6 characters long
        if len(new_password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return redirect('Security')

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
                <p style="color:  #000000;">Please use this OTP to complete your login process. Do not share this code with anyone. If you need a new OTP, you can click the 
                "Resend OTP Code" link in the system. Please note that if you do not click the link, the OTP code will remain the same.</p>
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

            # Check if the new password is the same as the old password
            if account.password == new_password:
                return JsonResponse({"success": False, "error": "This is your old password, make a new one."})
                
            account.password = new_password  # Save plain text as per your requirement
            account.save()
            
            return JsonResponse({"success": True, "message": "Password updated successfully!"})
            
        except AccountInformation.DoesNotExist:
            return JsonResponse({"success": False, "error": "Account not found."})

    return JsonResponse({"success": False, "error": "Invalid request."})



    
    
    

    







