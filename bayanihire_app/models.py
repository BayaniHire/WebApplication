from django.db import models

class AccountInformation(models.Model):
    account_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=45)
    password = models.CharField(max_length=45)
    last_name = models.CharField(max_length=45, blank=True, null=True)
    first_name = models.CharField(max_length=45, blank=True, null=True)
    middle_name = models.CharField(max_length=45, blank=True, null=True)
    house_no = models.CharField(max_length=45, blank=True, null=True)
    province = models.CharField(max_length=45, blank=True, null=True)
    barangay = models.CharField(max_length=45, blank=True, null=True)
    street_village = models.CharField(max_length=45, blank=True, null=True)
    city_municipality = models.CharField(max_length=45, blank=True, null=True)
    state = models.CharField(max_length=45, blank=True, null=True)
    zipcode = models.IntegerField(blank=True, null=True)
    email = models.EmailField(max_length=45, blank=True, null=True)
    mobile_number = models.BigIntegerField(blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    age = models.IntegerField(blank=True, null=True) 
    gender = models.CharField(max_length=45, blank=True, null=True)

    class Meta:
        db_table = 'account_information'


class AccountStorage(models.Model):
    role_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(AccountInformation, on_delete=models.CASCADE)
    role = models.CharField(max_length=45, blank=True, null=True)
    account_status = models.CharField(max_length=11, blank=True, null=True)

    class Meta:
        db_table = 'account_storage'


class JobDetailsAndRequirements(models.Model):
    job_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(AccountInformation, on_delete=models.CASCADE)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    job_company = models.CharField(max_length=50, blank=True, null=True)
    job_description = models.TextField(blank=True, null=True)
    job_benefits = models.TextField(blank=True, null=True)
    job_requirements = models.TextField(blank=True, null=True)
    job_status = models.CharField(max_length=7, blank=True, null=True)
    job_date_published = models.DateField(blank=True, null=True)

    class Meta:
        db_table = 'job_details_and_requirements'


class InterviewStorage(models.Model):
    interview_applicant_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(AccountInformation, on_delete=models.CASCADE)
    role = models.ForeignKey(AccountStorage, on_delete=models.CASCADE)
    interview_schedule_date = models.DateField(blank=True, null=True)
    interviewer_name = models.CharField(max_length=50, blank=True, null=True)
  
    class Meta:
        db_table = 'interview_storage'

class ListOfApplicantsWithStatusAndCredentials(models.Model):
    applicant_status_id = models.AutoField(primary_key=True)
    role = models.ForeignKey(AccountStorage, on_delete=models.CASCADE)
    account = models.ForeignKey(AccountInformation, on_delete=models.CASCADE)
    job = models.ForeignKey(JobDetailsAndRequirements, on_delete=models.CASCADE)
    interview_applicant_id = models.ForeignKey(InterviewStorage, null=True, blank=True, on_delete=models.CASCADE)
    applicant_status = models.CharField(max_length=30, blank=True, null=True)
    credentials = models.BinaryField(blank=True, null=True)
    file_metadata = models.TextField(blank=True, null=True)
    submission_date = models.DateField(blank=True, null=True)
    applicant_schedule_date = models.DateField(blank=True, null=True)
    admin_message = models.TextField(blank=True, null=True)
    interviewer_feedback = models.TextField(blank=True, null=True)
    interviewer_feedback_status = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = 'list_of_applicants_with_status_and_credentials'
        
class OTPVerification(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    account = models.ForeignKey(
        AccountInformation,
        on_delete=models.CASCADE,
        null=True,  # Allow null for existing rows
        blank=True  # Allow blank in forms or admin if needed
    )

    def is_expired(self):
        from django.utils.timezone import now, timedelta
        return now() > self.created_at + timedelta(minutes=30)

    
    def __str__(self):
        return f"OTP for {self.email} - {self.otp}"

