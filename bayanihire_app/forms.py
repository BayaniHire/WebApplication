from django import forms
from .models import AccountInformation, AccountStorage
from datetime import date 
from django.core.exceptions import ValidationError
import re


class AccountInformationForm(forms.ModelForm):
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'required': True}),
        label="Confirm Password"
    )

    class Meta:
        model = AccountInformation
        fields = [
            'first_name', 'middle_name', 'last_name', 'username', 
            'password', 'house_no', 'street_village', 'barangay', 
            'city_municipality', 'province', 'state', 'zipcode', 
            'email', 'mobile_number', 'birth_date', 'age', 'gender'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name', 'required': True}),
            'middle_name': forms.TextInput(attrs={'placeholder': 'Middle Name', 'required': True}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name', 'required': True}),
            'house_no': forms.TextInput(attrs={'placeholder': 'House No.', 'required': True}),
            'street_village': forms.TextInput(attrs={'placeholder': 'Street/Village', 'required': True}),
            'barangay': forms.TextInput(attrs={'placeholder': 'Barangay', 'required': True}),
            'city_municipality': forms.TextInput(attrs={'placeholder': 'City/Municipality', 'required': True}),
            'province': forms.TextInput(attrs={'placeholder': 'Province', 'required': True}),
            'state': forms.TextInput(attrs={'placeholder': 'State', 'required': True}),
            'zipcode': forms.TextInput(attrs={'placeholder': 'Zip Code', 'required': True}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email Address', 'required': True}),
            'mobile_number': forms.TextInput(attrs={'placeholder': 'Mobile Number', 'required': True}),
            'birth_date': forms.DateInput(attrs={'type': 'date', 'required': True}),
            'username': forms.TextInput(attrs={'placeholder': 'Username', 'required': True}),
            'password': forms.PasswordInput(attrs={'placeholder': 'Password', 'required': True}),
            'gender': forms.Select(attrs={'required': True}, choices=[
                ('male', 'Male'),
                ('female', 'Female'),
                ('prefer-not-to-say', 'Prefer not to say'),
            ]),
        }

    def clean_username(self):
            username = self.cleaned_data.get('username')
            # Append the email domain (@bynhr.com)
            if username and not username.endswith('@bynhr.com'):
                username = f'{username}@bynhr.com'
            return username

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date:
            today = date.today()
            age = today.year - birth_date.year - (
                (today.month, today.day) < (birth_date.month, birth_date.day)
            )
            # Check age limits
            if age < 18 or age > 65:
                raise ValidationError("Sorry, but the age requirement is 18-65 years old.")
            self.cleaned_data['age'] = age
        return birth_date


    def clean_password(self):
        password = self.cleaned_data.get('password')
        # Check password length
        if password and len(password) < 6:
            raise ValidationError("Your password is too short! You need 6+ characters.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
    
        # Check if passwords match
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords don't match.")
    
        return cleaned_data  # Ensure this line is included to return cleaned data

    def save(self, commit=True):
        instance = super().save(commit=False)  # Save without committing initially
    
        # Ensure mobile_number starts with '09' and retains leading zero
        if instance.mobile_number and not instance.mobile_number.startswith("09"):
            instance.mobile_number = f"0{instance.mobile_number}"
    
        # Additional logic, e.g., setting age if needed
        if 'birth_date' in self.cleaned_data:
            birth_date = self.cleaned_data['birth_date']
            today = date.today()
            instance.age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
        if commit:
            instance.save()  # This line actually saves the instance to the database
        return instance
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
    
        # Check if the username already contains the domain
        if username and not username.endswith('@bynhr.com'):
            username = f"{username}@bynhr.com"
    
        # Check if the username with domain already exists
        if AccountInformation.objects.filter(username=username).exists():
            raise ValidationError("Username is already taken.")
    
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if AccountInformation.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email
    
    def clean_mobile_number(self):
        mobile_number = self.cleaned_data.get('mobile_number')
        
        if not mobile_number:
            raise ValidationError("Mobile number is required.")
        
        if not mobile_number.isdigit():
            raise ValidationError("Mobile number must contain only numbers.")
        
        if len(mobile_number) != 11:
            raise ValidationError("Mobile number must be exactly 11 digits.")
        
        if not mobile_number.startswith("09"):
            raise ValidationError("Mobile number must start with '09'.")
        
        return mobile_number

    

class AdminAccountSetupForm(forms.ModelForm):  # Use the form name from your views.py
    role = forms.ChoiceField(choices=[('admin', 'Admin'), ('interviewer', 'Interviewer')], required=True)  # Define role manually

    class Meta:
        model = AccountInformation
        fields = ['first_name', 'middle_name', 'last_name', 'birth_date', 'gender']  # Ensure you list all the necessary fields

        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'gender': forms.Select(choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')]),
            'first_name': forms.TextInput(attrs={'placeholder': 'Enter First Name'}),
            'middle_name': forms.TextInput(attrs={'placeholder': 'Enter Middle Name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Enter Last Name'}),
        }

    def save(self, commit=True):
        account_info = super().save(commit=False)

        # Calculate age
        birth_date = self.cleaned_data['birth_date']
        today = date.today()
        account_info.age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

        # Generate username and password
        first_name = self.cleaned_data['first_name'].lower()
        last_name = self.cleaned_data['last_name'].lower()
        account_info.username = f"{first_name}{last_name}@bynhr.com"
        account_info.password = birth_date.strftime('%B%Y').lower()

        if commit:
            account_info.save()

            # Save role to AccountStorage
            account_storage = AccountStorage(
                account=account_info,
                role=self.cleaned_data['role'],
                account_status='Active'
            )
            account_storage.save()

        return account_info
