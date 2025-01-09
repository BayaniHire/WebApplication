from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', views.Index, name = "Index" ),
    path('login/', views.login, name = "login"),
    path('Registration/', views.Registration, name = "Registration"),
    path('ForgotPassword/',views.ForgotPassword, name = 'ForgotPassword'),
    path('EmailConfirmation/', views.EmailConfirmation, name = 'EmailConfirmation'),
    path('FchangePassword/', views.FchangePassword, name = 'FchangePassword'),
    path('security/', views.Security, name='Security'),
    
     ##########INTERVIEWER###########################
    path('dashboard_interviewer/', views.interviewer_appointments, name='INTappointments'),
    path('profile_interviewer/', views.interviewer_profile, name='INTprofile'),
    path('applicants/', views.interviewer_applicants, name='INTapplicants'),
    path('viewinfo/<int:applicant_status_id>/', views.interviewer_viewinfo, name='INTviewinfo'),
    path('editfeedback/<int:applicant_status_id>/', views.interviewer_editfeedback, name='INTeditfeedback'),
    path('feedback/', views.interviewer_feedback, name='INTfeedback'),
    path('history/', views.interviewer_history, name='INThistory'),
    ##########INTERVIEWER###########################
##########################APPLICANT###############################################
    path('dashboard_applicant/', views.applicant_homepage, name='homepage'),
    path('jobreq/<int:job_id>/', views.applicant_jobreq, name='jobreq'),
    path('fileupload/<int:job_id>/', views.applicant_fileupload, name='fileupload'),
    path('applicationstatus/', views.applicant_applicationstatus, name='applicationstatus'),
    path('viewfileupload/<int:applicant_status_id>/', views.applicant_viewfileupload, name='viewfileupload'),
    path('interviewdetails/<int:applicant_status_id>/', views.applicant_interviewdetails, name='interviewdetails'),
    path('profile_applicant/', views.applicant_profile, name='profile'),
##########################APPLICANT###############################################
    path('generate-pdf/', generate_pdf, name='generate_pdf'),
#######################GENERATE PDF#################################
 ##########################ADMIN##########################################
    path('logout/', views.logout_view, name='logout'),
    path('dashboard_admin/', views.list_of_applicants, name='list_of_applicants'),
    path('open_applicants/<int:applicant_status_id>/', views.open_applicants, name='open_applicants'),
    path('view-file/<str:file_name>/', views.viewing_files, name='viewing_files'),  # Update this line
    path('list_of_jobs/', views.list_of_jobs, name='list_of_jobs'),
    path('create_job_details/', views.create_job_details, name='create_job_details'),
    path('edit-job/<int:job_id>/', views.edit_job_details, name='edit_job_details'), 
    path('qualification/', views.qualification, name='qualification'),
    path('send_schedule/', views.send_schedule, name='send_schedule'),
    path('confirm_send_schedule/', views.confirm_send_schedule, name='confirm_send_schedule'),
    path('open_schedule_list/', views.open_schedule_list, name='open_schedule_list'),
    path('schedule/', views.schedule, name='schedule'),
    path('admin_feedback/', views.feedback, name='feedback'),
    path('view_feedback/<int:applicant_status_id>/', views.view_feedback, name='view_feedback'),
    path('profile_admin/', views.adminprofile, name='adminprofile'),
    path('add_accounts/', views.add_accounts, name='add_accounts'),
    path('manage_accounts/', views.manage_accounts, name='manage_accounts'),
    
    path('admin_interviewer_account_setup/', views.admin_interviewer_account_setup, name='admin_interviewer_account_setup'),
    path('admin_creatingjob/', views.admin_creatingjob, name='admin_creatingjob'),
    path('applicant/update/<int:applicant_status_id>/', views.update_applicant_status, name='update_applicant_status'),

    #### wag galawing sa update to###
    path('update_password/', views.update_password, name='update_password'),
    
    # Email Function
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('reset-password/', views.reset_password_view, name='reset_password_view'),
    path('force-change-password/', views.force_change_password, name='force_change_password'),
##########################ADMIN##########################################

    ###wag po galawin pang log in to
    path('security/change_password/', views.change_password, name='change_password'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
