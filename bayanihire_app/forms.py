from django import forms
from .models import AccountInformation, AccountStorage
from datetime import date 
from django.core.exceptions import ValidationError
import re


class AccountInformationForm(forms.ModelForm):
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm your password', 'required': True}),
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
            'first_name': forms.TextInput(attrs={'placeholder': 'e.g., Juan', 'required': True}),
            'middle_name': forms.TextInput(attrs={'placeholder': 'e.g., Santos (N/A if none)', 'required': True}),
            'last_name': forms.TextInput(attrs={'placeholder': 'e.g., Dela Cruz', 'required': True}),
            'house_no': forms.TextInput(attrs={'placeholder': 'e.g., 1234', 'required': True}),
            'street_village': forms.TextInput(attrs={'placeholder': 'e.g., Green Village', 'required': True}),
            'barangay': forms.TextInput(attrs={'placeholder': 'e.g., Barangay 123', 'required': True}),
            'city_municipality': forms.TextInput(attrs={'placeholder': 'e.g., Quezon City', 'required': True}),
            'province': forms.TextInput(attrs={'placeholder': 'e.g., Laguna, Cebu', 'required': True}),
            'state': forms.TextInput(attrs={
                'placeholder': 'Philippines', 
                'required': True, 
                'readonly': True,  
                'value': 'Philippines'  
            }),
            'zipcode': forms.TextInput(attrs={'placeholder': 'e.g., 4001', 'required': True}),
            'email': forms.EmailInput(attrs={'placeholder': 'example@gmail.com', 'required': True}),
            'mobile_number': forms.TextInput(attrs={'placeholder': '09xxxxxxxxx', 'required': True}),
            'birth_date': forms.DateInput(attrs={'type': 'date', 'required': True}),
            'username': forms.TextInput(attrs={'placeholder': 'juan12', 'required': True}),
            'password': forms.PasswordInput(attrs={'placeholder': 'use 6 or more characters', 'required': True}),
            'gender': forms.Select(attrs={'required': True}, choices=[
                ('prefer-not-to-say', 'Prefer not to say'),
                ('male', 'Male'),
                ('female', 'Female'),
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
        if not birth_date:
            raise ValidationError("Birth date cannot be empty.")
        today = date.today()
        age = today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
        if age < 18 or age > 65:
            raise ValidationError("Sorry, but the age requirement is 18-65 years old.")
        self.cleaned_data['age'] = age
        return birth_date


    def clean_password(self):
        password = self.cleaned_data.get('password', '').strip()
        if not password:
            raise ValidationError("Password cannot be empty or just spaces.")
        # Check password length
        if password and len(password) < 6:
            raise ValidationError("Your password is too short! You need 6+ characters.")
        return password

    def clean(self):
        cleaned_data = super().clean()

        # Check if any required field is all spaces
        for field, value in cleaned_data.items():
            if isinstance(value, str) and not value.strip():
                self.add_error(field, f"{field.replace('_', ' ').capitalize()} cannot be empty or just spaces.")

        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if not password or not confirm_password:
            self.add_error('password', "Password cannot be empty.")
            self.add_error('confirm_password', "Confirm Password cannot be empty.")
        elif password != confirm_password:
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

        if not username:
            raise ValidationError("Username cannot be empty or just spaces.")

        # Check if the username contains spaces
        if username and " " in username:
            raise ValidationError("Username must not contain spaces.")

        # Check if the username already contains the domain
        if username and not username.endswith('@bynhr.com'):
            username = f"{username}@bynhr.com"

        # Check if the username with domain already exists
        if AccountInformation.objects.filter(username=username).exists():
            raise ValidationError("Username is already taken.")

        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise ValidationError("Email cannot be empty or just spaces.")
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValidationError("Please enter a valid email address.")
        if AccountInformation.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email
    
    def clean_mobile_number(self):
        mobile_number = self.cleaned_data.get('mobile_number')  # Get the value of the field

        if mobile_number is None:  # Handle the None case explicitly
            mobile_number = ""

        mobile_number = mobile_number.strip()  # Strip any leading/trailing spaces

        if not mobile_number:  # Check if the field is empty after stripping
            raise ValidationError("Mobile number cannot be empty or just spaces.")

        if not mobile_number.isdigit():  # Ensure it contains only digits
            raise ValidationError("Mobile number must contain only numbers.")

        if len(mobile_number) != 11:  # Validate the length
            raise ValidationError("Mobile number must be exactly 11 digits.")

        if not mobile_number.startswith("09"):  # Ensure it starts with "09"
            raise ValidationError("Mobile number must start with '09'.")

        return mobile_number

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not first_name:
            raise ValidationError("First name cannot be empty or just spaces.")
        # Allow alphabetic characters and spaces
        if not re.match(r"^[a-zA-Z\s]+$", first_name):
            raise ValidationError("First name must contain only alphabetic characters and spaces.")
        if len(first_name) < 2:
            raise ValidationError("First name must be at least 2 characters long.")
        return first_name

    def clean_middle_name(self):
        middle_name = self.cleaned_data.get('middle_name')
        if middle_name and middle_name.upper() not in ["N/A", "NOT APPLICABLE"]:
            # Allow alphabetic characters and spaces for middle name
            if not re.match(r"^[a-zA-Z\s]+$", middle_name):
                raise ValidationError("Middle name must contain only alphabetic characters, spaces, or 'N/A'.")
            if len(middle_name) < 2:
                raise ValidationError("Middle name must be at least 2 characters long.")
        return middle_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not last_name:
            raise ValidationError("Last name cannot be empty or just spaces.")
        # Allow alphabetic characters and spaces
        if not re.match(r"^[a-zA-Z\s]+$", last_name):
            raise ValidationError("Last name must contain only alphabetic characters and spaces.")
        if len(last_name) < 2:
            raise ValidationError("Last name must be at least 2 characters long.")
        return last_name
        
    def clean_house_no(self):
        house_no = self.cleaned_data.get('house_no')

        if not house_no:
            raise ValidationError("House number cannot be empty or just spaces.")

        # Allow alphanumeric characters (letters and numbers), spaces, and optional dashes
        if not re.match(r"^[a-zA-Z0-9\s-]+$", house_no):
            raise ValidationError("House number must contain only letters, numbers, spaces, or dashes.")
        if len(house_no.strip()) < 1:
            raise ValidationError("House number must not be empty.")

        return house_no

    def clean_street_village(self):
        street_village = self.cleaned_data.get('street_village')  # Get the value of the field

        if street_village is None:  # Handle the None case explicitly
            street_village = ""

        street_village = street_village.strip()  # Strip any leading/trailing spaces

        if not street_village:  # Check if the field is empty after stripping
            raise ValidationError("Street or village cannot be empty or just spaces.")

        # Check if the input matches the allowed pattern
        if not re.match(r"^[a-zA-Z0-9\s.,-]+$", street_village):
            raise ValidationError("Street or village must contain only letters, numbers, spaces, commas, or hyphens.")

        if len(street_village) < 3:  # Ensure minimum length requirement
            raise ValidationError("Street or village must be at least 3 characters long.")

        return street_village
        
    def clean_barangay(self):
        barangay = self.cleaned_data.get('barangay')  # Get the value of the field

        if barangay is None:  # Handle the None case explicitly
            barangay = ""

        barangay = barangay.strip()  # Strip any leading/trailing spaces

        if not barangay:  # Check if the field is empty after stripping
            raise ValidationError("Barangay cannot be empty or just spaces.")

        # Check if the input matches the allowed pattern
        if not re.match(r"^[a-zA-Z0-9\s.,-]+$", barangay):
            raise ValidationError("Barangay must contain only letters, numbers, spaces, commas, or hyphens.")

        if len(barangay) < 3:  # Ensure minimum length requirement
            raise ValidationError("Barangay must be at least 3 characters long.")

        return barangay
        
    def clean_city_municipality(self):
        city_municipality = self.cleaned_data.get('city_municipality')  # Get the value of the field

        if city_municipality is None:  # Handle the None case explicitly
            city_municipality = ""

        city_municipality = city_municipality.strip()  # Strip any leading/trailing spaces

        if not city_municipality:  # Check if the field is empty after stripping
            raise ValidationError("City or municipality cannot be empty or just spaces.")

        # Check if the input matches the allowed pattern
        if not re.match(r"^[a-zA-Z\s]+$", city_municipality):
            raise ValidationError("City or municipality must contain only letters and spaces.")

        if len(city_municipality) < 2:  # Ensure minimum length requirement
            raise ValidationError("City or municipality must be at least 2 characters long.")

        return city_municipality

    def clean_province(self):
        province = self.cleaned_data.get('province')  # Get the value of the field

        if province is None:  # Handle the None case explicitly
            province = ""

        province = province.strip()  # Strip any leading/trailing spaces

        if not province:  # Check if the field is empty after stripping
            raise ValidationError("Province cannot be empty or just spaces.")

        # Validate that the input contains only letters and spaces
        if not re.match(r"^[a-zA-Z\s]+$", province):
            raise ValidationError("Province must contain only letters and spaces.")

        # Ensure minimum length requirement
        if len(province) < 2:
            raise ValidationError("Province must be at least 2 characters long.")

        return province

    def clean_state(self):
        state = self.cleaned_data.get('state')  # Get the value of the field

        if state is None:  # Handle the None case explicitly
            state = ""

        state = state.strip()  # Strip any leading/trailing spaces

        if not state:  # Check if the field is empty after stripping
            raise ValidationError("State cannot be empty or just spaces.")

        if state.lower() != "philippines":  # Enforce that the state must be 'Philippines'
            raise ValidationError("State must be 'Philippines'.")

        return "Philippines"  # Always return the fixed value

    
    def clean_zipcode(self):
        zipcode = self.cleaned_data.get('zipcode')  # Get the value of the field

        if zipcode is None:  # Handle the None case explicitly
            zipcode = ""

        zipcode = zipcode.strip()  # Strip any leading/trailing spaces

        if not zipcode:  # Check if the field is empty after stripping
            raise ValidationError("Zipcode cannot be empty or just spaces.")

        # Validate that the input contains exactly 4 digits
        if not re.match(r"^\d{4}$", zipcode):
            raise ValidationError("Zipcode must be exactly 4 digits.")

        # Validate that the value is within the valid Philippine zip code range
        if not (400 <= int(zipcode) <= 9811):
            raise ValidationError("Please input a valid Philippine zipcode.")

        return zipcode

    


    

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
