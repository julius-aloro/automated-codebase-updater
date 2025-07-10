from boto3.session import Session
from botocore.exceptions import SSOTokenLoadError, NoCredentialsError, UnauthorizedSSOTokenError
import boto3
import subprocess

def authenticate_session(profile: str):

    session = Session(profile_name=profile)
    client = session.client('sts')
    
    try:
        response = client.get_caller_identity()
        return session
        
    except (SSOTokenLoadError, NoCredentialsError, UnauthorizedSSOTokenError) as e:
        print('You are currently not logged in or your session has expired.')
        print('Opening SSO login...')
        subprocess.run(['aws', 'sso', 'login', '--profile', profile], check=True)

        # Try again after login
        session = boto3.Session(profile_name=profile)
        client = session.client('sts')
        response = client.get_caller_identity()
        print(f'Authenticated as {response['UserId'] :>50}')
        return session