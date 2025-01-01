import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bayanihire_app.settings')  # Replace 'your_project_name' with your actual project name
django.setup()

from bayanihire_app.models import OTPVerification, AccountInformation

# Populate the `account` field for all rows in OTPVerification
def populate_account_field():
    try:
        # Iterate through each OTPVerification entry
        otp_records = OTPVerification.objects.all()
        for otp in otp_records:
            # Find the matching AccountInformation entry based on email
            try:
                account = AccountInformation.objects.get(email=otp.email)
                otp.account = account
                otp.save()
                print(f"Updated OTP ID {otp.id} with account ID {account.account_id}")
            except AccountInformation.DoesNotExist:
                print(f"No matching account found for OTP ID {otp.id} with email {otp.email}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    populate_account_field()
