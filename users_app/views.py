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


def interviewer_applicants(request):
    return render(request, 'Applicants.html')

def interviewer_appointments(request):
    return render(request, 'Appointments.html')

def interviewer_editfeedback(request):
    return render(request, 'EditFeedback.html')

def interviewer_feedback(request):
    return render(request, 'Feedback.html')

def interviewer_history(request):
    return render(request, 'History.html')

def interviewer_profile(request):
    return render(request, 'Profile.html')

def interviewer_viewinfo(request):
    return render(request, 'ViewInfo.html')

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
    return render(request, 'AdminView_3_Qualification.html')

def send_schedule(request):
    return render(request, 'AdminView_3_1_Send.html')

def open_schedule_list(request):
    return render(request, 'AdminView_3_2_OpenScheduleList.html')

def schedule(request):
    return render(request, 'AdminView_4_Schedule.html')

def feedback(request):
    return render(request, 'AdminView_5_Feedback.html')

def view_feedback(request):
    return render(request, 'AdminView_5_1_ViewFeedback.html')

def adminprofile(request):
    return render(request, 'AdminView_6_Profile.html')

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

            # Ensure all required fields are provided
            if not (role and birthday and gender and first_name and last_name):
                return render(request, 'users_app/AdminView_6_2_AddAccounts.html', {"message": "Missing required fields. Please fill out the form completely."})

            # Check if the birthday is not empty and compute age
            birth_date = datetime.strptime(birthday, "%Y-%m-%d")
            today = datetime.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

            # Generate default username and password
            username = f"{first_name.lower().replace(' ', '')}@bynhr.com"  # Remove spaces from the first name
            password = last_name.lower().replace(' ', '')  # Use the last name as the default password and remove spaces

            # Step 1: Save data to AccountInformation
            account_info = AccountInformation(
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                birth_date=birth_date,
                gender=gender,
                username=username,
                password=password,
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
