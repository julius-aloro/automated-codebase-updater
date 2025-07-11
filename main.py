import boto3
import json
from auth import authenticate_session
from get_info import get_asg
from pathlib import Path
import subprocess


with open('masterfile.json') as f:
    masterfile = json.load(f)

base_folder = Path('~/cloned-repo/').expanduser()
backup_folder = Path(base_folder, 'backup')
edited_folder = Path(base_folder, 'edited')
stutalk_lt = []
evision_lt = []
ami_id = []

if not base_folder.exists():
    base_folder.mkdir()
if not backup_folder.exists():
    backup_folder.mkdir()
if not edited_folder.exists():
    edited_folder.mkdir()


for account in masterfile:

    profile_name = account['profile_name']
    session = authenticate_session(profile_name)

    ########################### GETTING ASG's ##############################
    auto_scaling = session.client('autoscaling').describe_auto_scaling_groups()
    for asg in auto_scaling['AutoScalingGroups']:
        if 'stutalk' in asg['LaunchTemplate']['LaunchTemplateName'].lower():
            stutalk_lt.append(asg['LaunchTemplate']['LaunchTemplateId'])
        elif 'evision' in asg['LaunchTemplate']['LaunchTemplateName'].lower():
            evision_lt.append((asg['LaunchTemplate']['LaunchTemplateId']))

        ########################### GETTING AMI ID's ##############################

        lt_version = session.client('ec2').describe_launch_template_versions(
            LaunchTemplateId=stutalk_lt[0], Versions=['$Latest',])
        
        lt_ami = lt_version['LaunchTemplateVersions'][0]['LaunchTemplateData'].get('ImageId')
        if lt_ami not in ami_id:
            ami_id.append(lt_ami)
        else:
            continue
    
    ########################### CLONING REPOSITORIES ##############################
    if not account['enabled']:
        continue
    else:
        repository_url = account['repo_url']
        success_message = '[CLONE SUCCESSFUL]'
        try:
            subprocess.run(["git", '-C', edited_folder , "clone", "--quiet", repository_url],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            check=True) # Hide Output

            print(f'{account['customer_name']} {success_message :>45}')

        except subprocess.CalledProcessError as e:
            print(f"Failed to clone {account['customer_name']} repository. Please resolve manually: {e}")
            exit (1)   # Make sure the script exits when a repo isn't cloned successfully

print(stutalk_lt)
print(evision_lt)
print(ami_id)