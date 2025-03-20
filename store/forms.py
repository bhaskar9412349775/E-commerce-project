from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, ShippingAddress, Review

class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'address', 'password1', 'password2']

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'address']

class AddressForm(forms.ModelForm):
    class Meta:
        model = ShippingAddress
        fields = ['first_name', 'last_name', 'street', 'apartment', 'city', 'state', 'country', 'zip_code', 'phone']
        widgets = {
            'apartment': forms.TextInput(attrs={'placeholder': 'Optional'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class CheckoutForm(forms.Form):
    shipping_address = forms.ModelChoiceField(
        queryset=None,
        empty_label="Select a saved address",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control mb-3'})
    )
    
    use_new_address = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['shipping_address'].queryset = ShippingAddress.objects.filter(user=user)
        
        # Add shipping address fields
        address_form = AddressForm()
        for field_name, field in address_form.fields.items():
            self.fields[field_name] = field

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '5',
                'step': '1'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share your thoughts about this product...'
            })
        }

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating < 1 or rating > 5:
            raise forms.ValidationError('Rating must be between 1 and 5.')
        return rating 