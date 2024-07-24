import os
import base64
import pandas as pd
from django.conf import settings
from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.contrib import messages
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from .forms import EmailForm
from django.contrib.auth import logout
from decouple import config

# Load these values from your .env file
GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = config('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = config('GOOGLE_REDIRECT_URI')

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Add this line for local development

# Rest of your code...


def google_login(request):
    if 'credentials' in request.session:
        return redirect('send_email')  # Redirect to the send_email view if already logged in
    
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": [GOOGLE_REDIRECT_URI],
                "javascript_origins": ["http://127.0.0.1:8000"]
            }
        },
        scopes=['https://www.googleapis.com/auth/gmail.send'],
        redirect_uri=GOOGLE_REDIRECT_URI
    )
    authorization_url, state = flow.authorization_url(access_type='offline')
    request.session['state'] = state
    return redirect(authorization_url)

def oauth2callback(request):
    state = request.session.get('state')
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": [GOOGLE_REDIRECT_URI],
                "javascript_origins": ["http://127.0.0.1:8000"]
            }
        },
        scopes=['https://www.googleapis.com/auth/gmail.send'],
        state=state,
        redirect_uri=GOOGLE_REDIRECT_URI
    )
    flow.fetch_token(authorization_response=request.get_full_path())

    credentials = flow.credentials
    request.session['credentials'] = credentials_to_dict(credentials)

    return redirect('send_email')


def logout_view(request):
    logout(request)
    return redirect('send_email')

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes,
    }

def send_email(request):
    is_logged_in = 'credentials' in request.session

    if request.method == 'POST':
        if not is_logged_in:
            return redirect('google_login')  # Redirect to Google login if not authenticated
        
        form = EmailForm(request.POST, request.FILES)
        if form.is_valid():
            email_file = form.cleaned_data['email_file']
            subject = form.cleaned_data['subject']
            body = form.cleaned_data['body']

            # Ensure MEDIA_ROOT directory exists
            if not os.path.exists(settings.MEDIA_ROOT):
                os.makedirs(settings.MEDIA_ROOT)

            # Save the uploaded file
            email_file_path = os.path.join(settings.MEDIA_ROOT, email_file.name)

            with open(email_file_path, 'wb+') as destination:
                for chunk in email_file.chunks():
                    destination.write(chunk)

            try:
                df = pd.read_excel(email_file_path)
                if 'Email' not in df.columns or 'Name' not in df.columns or 'Company' not in df.columns:
                    messages.error(request, "The uploaded file must contain 'Email', 'Name', and 'Company' columns.")
                    return redirect('send_email')
                
                emails = df[['Email', 'Name', 'Company']].dropna().to_dict('records')

                credentials = Credentials(**request.session.get('credentials'))
                service = build('gmail', 'v1', credentials=credentials)

                for record in emails:
                    personalized_body = body.replace("{name}", record['Name']).replace("{company}", record['Company'])
                    message = {
                        'raw': base64.urlsafe_b64encode(
                            f"To: {record['Email']}\r\n"
                            f"Subject: {subject}\r\n"
                            f"\r\n"
                            f"{personalized_body}".encode('utf-8')
                        ).decode('utf-8')
                    }
                    service.users().messages().send(userId='me', body=message).execute()

                messages.success(request, "Emails sent successfully!")
            except Exception as e:
                messages.error(request, f"An error occurred: {e}")
            finally:
                if os.path.exists(email_file_path):
                    os.remove(email_file_path)

            return redirect('send_email')
    else:
        form = EmailForm()

    return render(request, 'email_app/send_email.html', {'form': form, 'is_logged_in': is_logged_in})

def already_logged_in(request):
    return HttpResponse("You are already logged in with Google.")
