from django.urls import path
from . import views

urlpatterns = [
    path('', views.Index, name = "Index" ),
    path('login/', views.login, name = "login"),
    path('Registration/', views.Registration, name = "Registration"),
    path('ForgotPassword/',views.ForgotPassword, name = 'ForgotPassword'),
    path('EmailConfirmation/', views.EmailConfirmation, name = 'EmailConfirmation'),
    path('FchangePassword/', views.FchangePassword, name = 'FchangePassword'),
    
    path('dashboard_interviewer/', views.interviewer_appointments, name='INTappointments'),
    path('profile_interviewer/', views.interviewer_profile, name='INTprofile'),
    path('applicants/', views.interviewer_applicants, name='INTapplicants'),
    path('viewinfo/', views.interviewer_viewinfo, name='INTviewinfo'),
    path('editfeedback/', views.interviewer_editfeedback, name='INTeditfeedback'),
    path('feedback/', views.interviewer_feedback, name='INTfeedback'),
    path('history/', views.interviewer_history, name='INThistory'),
    
    path('dashboard_applicant/', views.applicant_homepage, name='homepage'),
    path('jobreq/<str:job_type>/', views.applicant_jobreq, name='jobreq'),
    path('profile_applicant/', views.applicant_profile, name='profile'),
    path('applicationstatus/', views.applicant_applicationstatus, name='applicationstatus'),
    path('jobreq/', views.applicant_jobreq, name='jobreq'),
    path('fileupload/', views.applicant_fileupload, name='fileupload'),
    path('viewfileupload/', views.applicant_viewfileupload, name='viewfileupload'),
    path('interviewdetails/', views.applicant_interviewdetails, name='interviewdetails'),
    
    path('dashboard_admin/', views.list_of_applicants, name='list_of_applicants'),
    path('open_applicants/', views.open_applicants, name='open_applicants'),
    path('viewing_files/', views.viewing_files, name='viewing_files'),
    path('list_of_jobs/', views.list_of_jobs, name='list_of_jobs'),
    path('edit_job_details/', views.edit_job_details, name='edit_job_details'),
    path('qualification/', views.qualification, name='qualification'),
    path('send_schedule/', views.send_schedule, name='send_schedule'),
    path('open_schedule_list/', views.open_schedule_list, name='open_schedule_list'),
    path('schedule/', views.schedule, name='schedule'),
    path('admin_feedback/', views.feedback, name='feedback'),
    path('view_feedback/', views.view_feedback, name='view_feedback'),
    path('profile_admin/', views.adminprofile, name='adminprofile'),
    path('add_accounts/', views.add_accounts, name='add_accounts'),
    path('manage_accounts/', views.manage_accounts, name='manage_accounts'),
    
    ###wag galawin pang admin to
    path('admin_interviewer_account_setup/', views.admin_interviewer_account_setup, name='admin_interviewer_account_setup'),
    path('admin_creatingjob/', views.admin_creatingjob, name='admin_creatingjob'),

]