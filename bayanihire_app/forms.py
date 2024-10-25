from django import forms
from .models import AccountInformation, AccountStorage
from datetime import date 

class AccountInformationForm(forms.ModelForm):
    class Meta:
        model = AccountInformation
        fields = [
            'first_name', 'middle_name', 'last_name', 'username', 
            'password', 'house_no', 'street_village', 'barangay',  # Added new fields
            'city_municipality', 'province', 'state', 'zipcode',  # Added state field
            'email', 'mobile_number', 'birth_date', 'age', 'gender'
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),  # Birthdate input as date type
            'gender': forms.Select(choices=[
                ('male', 'Male'),
                ('female', 'Female'),
                ('prefer-not-to-say', 'Prefer not to say'),
            ]),
            'password': forms.PasswordInput(),
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
            # Calculate age
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            self.cleaned_data['age'] = age  # Store age in cleaned_data
        return birth_date

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Ensure age is calculated and saved
        if 'birth_date' in self.cleaned_data:
            birth_date = self.cleaned_data['birth_date']
            today = date.today()
            instance.age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        
        if commit:
            instance.save()
        return instance
    

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