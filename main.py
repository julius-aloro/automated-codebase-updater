import boto3
import json
from auth import authenticate_session
from get_info import get_asg


with open('masterfile.json') as f:
    masterfile = json.load(f)

stutalk_lt = []
evision_lt = []


for accounts in masterfile:

    profile_name = accounts['profile_name']
    session = authenticate_session(profile_name)

    response = session.client('autoscaling').describe_auto_scaling_groups()
    for asg in response['AutoScalingGroups']:
        if 'stutalk' in asg['LaunchTemplate']['LaunchTemplateName'].lower():
            stutalk_lt.append(asg['LaunchTemplate']['LaunchTemplateId'])
        elif 'evision' in asg['LaunchTemplate']['LaunchTemplateName'].lower():
            evision_lt.append((asg['LaunchTemplate']['LaunchTemplateId']))

