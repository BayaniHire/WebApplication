from django.shortcuts import render, redirect
from django.http import HttpResponse
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
    return render(request, 'EditFeedback.html')

def interviewer_feedback(request):
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


def interviewer_history(request):
    # Assuming the user's ID is stored in session
    user_id = request.session.get('user_id')
    
    # Retrieve feedback entries linked to the current user
    applicants = ListOfApplicantsWithStatusAndCredentials.objects.filter(
        interview_applicant_id__account_id=user_id,
        interviewer_feedback__isnull=False
    ).order_by('-submission_date')
    
    return render(request, 'History.html', {'applicants': applicants})

def interviewer_profile(request):
    return render(request, 'Profile.html')

def interviewer_viewinfo(request, applicant_status_id):
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
    jobs = JobDetailsAndRequirements.objects.filter(job_status='ACTIVE')  # Fetch only active jobs
    context = {
        'jobs': jobs  # Pass the jobs to the template context
    }
    return render(request, 'Applicant_homepage.html', context)


def applicant_jobreq(request, job_id):
    job_details = get_object_or_404(JobDetailsAndRequirements, job_id=job_id)

    return render(request, 'Applicant_JobReq.html', {'job_details': job_details})

def applicant_fileupload(request, job_id):
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

        # Initialize a list to hold file names for metadata and file contents
        file_metadata_list = []
        combined_file_content = b''  # Use bytes for combining file contents

        # Process each uploaded file
        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name
            file_metadata_list.append(file_name)  # Collect file names

            # Read the file content into a separate variable to keep track of sizes
            file_content = uploaded_file.read()  # Read file content
            combined_file_content += file_content  # Combine file contents into a single blob

        # Save a single instance with all the combined contents and metadata
        new_application = ListOfApplicantsWithStatusAndCredentials(
            job=job_instance,
            role=role_instance,
            account=account,
            credentials=combined_file_content,  # Store combined file contents
            file_metadata=', '.join(file_metadata_list),  # Store concatenated file names
            submission_date=timezone.now().date(),
            applicant_status="UNDER REVIEW"
        )
        new_application.save()

        # Render the template with success message and uploaded files
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
        .select_related('job') 
        .order_by('-submission_date') # Ensure you can access job-related fields
        .annotate(
            interview_schedule_date=InterviewStorage.objects.filter(account=account).values('interview_schedule_date')[:1]
        )  # Annotate to include interview date
        .values(
            'job__job_title',
            'job__job_date_published',  # Ensure this field exists in the job model
            'applicant_status',
            'submission_date',
            'interview_schedule_date',
            'applicant_status_id',
        )
        .distinct()  
    )
    

    context = {
        'applications': applications,  # Pass the applications to the template
        'has_applications': applications.exists()  # Flag to check if applications exist
    }

    

    return render(request, 'Applicant_Applicationstatus.html', context)

def applicant_viewfileupload(request, applicant_status_id):
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

def applicant_interviewdetails(request):
    return render(request, 'Applicant_InterviewDetails.html')

def applicant_profile(request):
    return render(request, 'Applicant_profile.html')


###################APPLICANT############################



##########################Admin###############################################
logger = logging.getLogger(__name__)

def list_of_applicants(request):
    # Get all applicants
    applicants = ListOfApplicantsWithStatusAndCredentials.objects.all()
    print(applicants)

    # Calculate total number of applicants
    total_applicants = applicants.count()
    print(total_applicants)

    # Prepare data for the table
    applicant_data = []
    for idx, applicant in enumerate(applicants, start=1):
        account_info = applicant.account  # Assuming this is the relation to AccountInformation
        job_details = applicant.job        # Assuming this is the relation to JobDetailsAndRequirements

        # Build the applicant row
        applicant_data.append({
            'no': idx,
            'full_name': f"{account_info.first_name} {account_info.middle_name or ''} {account_info.last_name}",
            'company': job_details.job_company,
            'position_applied': job_details.job_title,
            'date_applied': applicant.submission_date,  # Assuming this is the correct field
            'status': applicant.applicant_status,
            'applicant_status_id': applicant.applicant_status_id,  # Make sure this line is added
        })

    context = {
        'applicant_data': applicant_data,
        'total_applicants': total_applicants,
    }
    return render(request, 'AdminView_1_Homepage_ListofApplicants.html', context)

def open_applicants(request, applicant_status_id):
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
    return render(request, 'AdminView_1_1_OpenApplicants.html', context)

def update_applicant_status(request, applicant_status_id):
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
    jobs = JobDetailsAndRequirements.objects.all()  # Fetch all job details
    active_jobs_count = JobDetailsAndRequirements.objects.filter(job_status="ACTIVE").count()  # Count active jobs
    return render(request, 'AdminView_2_ListofJobs.html', {
        'jobs': jobs,
        'active_jobs_count': active_jobs_count  # Pass count to the template
    })

def edit_job_details(request, job_id):
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
    today_date = date.today().strftime("%Y-%m-%d")  # Format today's date as YYYY-MM-DD
    return render(request, 'AdminView_2_2_CreateJobDetails.html', {'today_date': today_date})


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
    
def send_schedule(request):
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
    interviewer_name = request.GET.get('interviewer', None)
    search_query = request.GET.get('search', '')
    view_all = request.GET.get('view_all', '')

    if view_all:
        applicants = ListOfApplicantsWithStatusAndCredentials.objects.all()
    elif interviewer_name:
        interviews = InterviewStorage.objects.filter(interviewer_name=interviewer_name)
        applicants = ListOfApplicantsWithStatusAndCredentials.objects.filter(
            interview_applicant_id__in=interviews,
            account__first_name__icontains=search_query
        ).distinct()
    else:
        applicants = ListOfApplicantsWithStatusAndCredentials.objects.none()

    # Correcting the distinct interviewer query to use the correct primary key field
    interviewer_ids = InterviewStorage.objects.values('interviewer_name').annotate(max_id=Max('interview_applicant_id')).values('max_id')
    interviewers = InterviewStorage.objects.filter(interview_applicant_id__in=interviewer_ids)

    return render(request, 'AdminView_3_2_OpenScheduleList.html', {'applicants': applicants, 'interviewers': interviewers})

def schedule(request):
    # Get AccountStorage entries where the role is 'interviewer'
    interviewers = AccountStorage.objects.filter(role='interviewer').select_related('account')
    
    # Extract full names from related AccountInformation records
    interviewer_names = [
        f"{i.account.first_name or ''} {i.account.middle_name or ''} {i.account.last_name or ''}".strip()
        for i in interviewers
    ]

    if request.method == "POST":
        # Retrieve the selected interviewer name and interview date from the form
        selected_interviewer_name = request.POST.get('selected_interviewer')
        interview_date = request.POST.get('interview_date')

        # Find the selected interviewer in AccountStorage by matching full name
        selected_interviewer = next(
            (i for i in interviewers if f"{i.account.first_name or ''} {i.account.middle_name or ''} {i.account.last_name or ''}".strip() == selected_interviewer_name), 
            None
        )

        if selected_interviewer:
            # Save the interview schedule date in InterviewStorage with concatenated full name
            InterviewStorage.objects.create(
                account=selected_interviewer.account,
                role=selected_interviewer,
                interview_schedule_date=interview_date,
                interviewer_name=selected_interviewer_name,  # Save full name as concatenated interviewer_name
            )

        # Redirect to the same page with a success message
        return redirect('schedule')

    # Retrieve interview records with interviewer names and scheduled dates for display
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

    # Pass interviewer names and interview schedule data to the template
    context = {
        'interviewer_names': interviewer_names,
        'formatted_interview_data': formatted_interview_data,
    }
    return render(request, 'AdminView_4_Schedule.html', context)

def schedule_view(request):
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
    applicants = ListOfApplicantsWithStatusAndCredentials.objects.select_related('account', 'job').all()
    first_applicant_id = applicants.first().applicant_status_id if applicants.exists() else None
    return render(request, 'AdminView_5_Feedback.html', {
        'applicants': applicants,
        'first_applicant_id': first_applicant_id
    })

@require_http_methods(["GET", "POST"])
def view_feedback(request, applicant_status_id):
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
    return render(request, 'AdminView_6_2_AddAccounts.html')

def manage_accounts(request):
    return render(request, 'AdminView_6_1_manage_accounts.html')

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

def admin_interviewer_account_setup(request):
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


############################index##########################################
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
                    messages.error(request, "Account is deactivated. Please contact support.")
                    return render(request, 'login.html')
                
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
