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


def applicant_homepage(request):
    return render(request, 'Applicant_homepage.html')

def applicant_profile(request):
    return render(request, 'Applicant_profile.html')

def applicant_applicationstatus(request):
    return render(request, 'Applicant_Applicationstatus.html')

def applicant_jobreq(request, job_type):
    job_details = {}
    if job_type == "doctor":
        job_details = {
            "title": "Doctor",
            "date_published": "01/01/2024",
            "description": "A doctor diagnoses and treats illnesses and injuries in patients. They conduct physical exams, order and interpret diagnostic tests, and develop treatment plans. Doctors also provide preventive care and educate patients about health and wellness.",
            "requirements": "Medical degree, relevant certifications, at least 3 years of experience in a medical field.",
            "benefits": "Healthcare coverage, pension, 30 days vacation, paid time off, professional development programs."
        }
    elif job_type == "teacher":
        job_details = {
            "title": "Teacher",
            "date_published": "01/02/2024",
            "description": "A teacher imparts knowledge and skills to students, fosters a supportive learning environment, and develops lesson plans to aid student progress.",
            "requirements": "Teaching degree, state certifications, experience in lesson planning and classroom management.",
            "benefits": "Pension, summer vacation, 20 days paid time off, professional development courses."
        }
    elif job_type == "helper":
        job_details = {
            "title": "Helper",
            "date_published": "01/03/2024",
            "description": "A helper provides assistance with daily tasks, helping to ensure smooth operations in non-medical environments.",
            "requirements": "Basic experience in assisting roles, strong organizational skills, ability to multitask.",
            "benefits": "Flexible hours, healthcare coverage, 15 days paid vacation."
        }

    return render(request, 'Applicant_JobReq.html', {'job_details': job_details})

def applicant_fileupload(request):
    return render(request, 'Applicant_fileupload.html')

def applicant_viewfileupload(request):
    return render(request, 'Applicant_Viewfileupload.html')

def applicant_interviewdetails(request):
    return render(request, 'Applicant_InterviewDetails.html')



def list_of_applicants(request):
    return render(request, 'AdminView_1_Homepage_ListofApplicants.html')

def open_applicants(request):
    return render(request, 'AdminView_1_1_OpenApplicants.html')

def viewing_files(request):
    return render(request, 'AdminView_1_2_ViewingFiles.html')

def list_of_jobs(request):
    return render(request, 'AdminView_2_ListofJobs.html')

def edit_job_details(request):
    return render(request, 'AdminView_2_1_EditJobDetails.html')

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



def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Authenticate the user
        try:
            account = AccountInformation.objects.get(username=username, password=password)
            
            # Check role from AccountStorage
            account_storage = AccountStorage.objects.filter(account=account).first()
            
            if account_storage:
                # Store account ID in the session
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

    return render(request, 'logIn.html')