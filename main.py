import json
from auth import authenticate_session
from get_info import get_asg
from pathlib import Path
import subprocess
import re
import os
import stat
import shutil
import tempfile
import datetime

formatted_date = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

with open('masterfile.json') as f:
    masterfile = json.load(f)

base_folder = Path(tempfile.gettempdir()) / 'automated-codebase-updater'
backup_folder = Path(base_folder, 'backup')
edited_folder = Path(base_folder, 'edited')
stutalk_lt = []
evision_lt = []
ami_id = ''

########################### CLONING REPOSITORIES ##############################
def clone_repo(account):
    if not base_folder.exists():
        base_folder.mkdir()
    if not backup_folder.exists():
        backup_folder.mkdir()
    if not edited_folder.exists():
        edited_folder.mkdir()
    # ADD DELETE EXISTING FOLDERS HERE  <--------

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

############################ GETTING ASG's ##############################
def get_lt():
    auto_scaling = session.client('autoscaling').describe_auto_scaling_groups()
    for asg in auto_scaling['AutoScalingGroups']:
        if 'stutalk' in asg['LaunchTemplate']['LaunchTemplateName'].lower():
            stutalk_lt.append(asg['LaunchTemplate']['LaunchTemplateId'])
        elif 'evision' in asg['LaunchTemplate']['LaunchTemplateName'].lower():
            evision_lt.append((asg['LaunchTemplate']['LaunchTemplateId']))

########################## GETTING AMI ID's ##############################
def get_ami(session):
    lt_version = session.client('ec2').describe_launch_template_versions(
        LaunchTemplateId=stutalk_lt[0], Versions=['$Latest',])
    
    lt_ami = lt_version['LaunchTemplateVersions'][0]['LaunchTemplateData'].get('ImageId')
    global ami_id 
    ami_id = lt_ami

########################## UPDATING AMI ID's #############################
# Function for V1
def update_ami_v1(ami_id, repo_dir, target_file):
    with open(Path(edited_folder, repo_dir, target_file), 'r') as file:
        content = file.read()
        
    pattern = r'(\s*default\s*=\s*")(ami-[^"]+)(")'
    replace = r'\1' + ami_id + r'\3'
    new_content = re.sub(pattern, replace, content)

    with open(Path(edited_folder, repo_dir, target_file), 'w') as file:
        file.write(new_content)

#Function for V2
def update_ami_v2(ami_id, repo_dir, target_file):
    with open(Path(edited_folder, repo_dir, target_file), 'r') as file:
        content = file.read()
        
    pattern1 = r'(evision_image_id\s*=\s*")(ami-[^"]+)(")' # [^"] = Match anything except whats inside the brackets
    pattern2 = r'(stutalk_image_id\s*=\s*")(ami-[^"]+)(")'
    replace = r'\1' + ami_id + r'\3'
    content2 = re.sub(pattern1, replace, content)
    final_content = re.sub(pattern2, replace, content2)

    with open(Path(edited_folder, repo_dir, target_file), 'w') as file:
        file.write(final_content)


def backup():
    if os.path.exists(backup_folder):
        shutil.copytree(
            Path(edited_folder, account['repo_name']),
            Path(backup_folder, account['repo_name'])
        )

def remove_readonly(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)  # remove read-only flag
    func(path)

def git_checks_porcelain():
    repo_dir = Path(base_folder, edited_folder, account['repo_name'])
    result = subprocess.run(['git', '-C', str(repo_dir), 'status', '--porcelain'],
    capture_output=True,
    text=True
    )
    return result.stdout

def change_validations():
    repo_dir = Path(base_folder, edited_folder, account['repo_name'])
    result = subprocess.run(['git', '-C', str(repo_dir), 'diff'],
                    capture_output=True,
                    text=True
                    )
    return result.stdout

if base_folder.exists():
        os.chmod(base_folder, stat.S_IWRITE)
        shutil.rmtree(base_folder, onerror=remove_readonly)  # onerror = call remove_readonly function (Make it writable)

for account in masterfile:
    if not ['enabled']:
        continue
    else:
        profile_name = account['profile_name']
        session = authenticate_session(profile_name)
        get_lt()
        get_ami(session)
        clone_repo(account)
        backup()

        if account['version'] == 'v1':
            repo_dir = Path(base_folder, edited_folder, account['repo_name'])
            update_ami_v1(ami_id, repo_dir, 'ami_refresh.tf')
        elif account['version'] == 'v2':
            repo_dir = Path(base_folder, edited_folder, account['repo_name'])
            update_ami_v2(ami_id, repo_dir, 'main.tf')

        repo_dir = Path(base_folder, edited_folder, account['repo_name'])
        if not git_checks_porcelain():
            continue
        else:
            output = change_validations()
            print(output)
            logfile = Path(base_folder) / f'{formatted_date}-runlogs.txt'
            with open (logfile, 'a') as f:
                f.write('\n\n' + '=' * 60 + '\n')
                f.write(f'• Repo Name : {account['repo_name']} \n')
                f.write(f'• Changes Done :  \n')
                f.write('=' * 60 + '\n\n')
                f.write(output)