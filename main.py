import json
from auth import authenticate_session
from pathlib import Path
import subprocess
import re
import os
import stat
import shutil
import tempfile
import datetime
from getpass import getpass

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

########################### CLONING REPOSITORIES ##############################
def clone_repo(account, username, password):
    if not base_folder.exists():
        base_folder.mkdir()
    if not backup_folder.exists():
        backup_folder.mkdir()
    if not edited_folder.exists():
        edited_folder.mkdir()

    repository_url = f"https://{username}:{password}@{account['repo_url']}"
    try:
        subprocess.run(["git", '-C', edited_folder , "clone", "--quiet", repository_url],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True) # Hide Output

        print('\n' + '=' * 60 + '\n')
        print(f'• Cloned Repo : {account['customer_name']} \n')
        print('=' * 60 + '\n')

        shutil.copytree(
        Path(edited_folder, account['repo_name']),
        Path(backup_folder, account['repo_name'])
    )

    except subprocess.CalledProcessError as e:
        print(f"Failed to clone {account['customer_name']} repository. Please resolve manually: {e}")
        exit (1)   # Make sure the script exits when a repo isn't cloned successfully

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
    result = subprocess.run(['git', '-C', repo_dir, 'diff'],
                    capture_output=True,
                    text=True
                    )
    return result.stdout

def git_push():
    try:
        repo_dir = Path(base_folder, edited_folder, account['repo_name'])
        commit_message = f"AMI Refresh Code Base Update (Py Script) - {formatted_date}"
        
        result = subprocess.run(
        ['git', '-C', repo_dir, 'status', '--porcelain'],
        capture_output=True,
        text=True
    )
        if result.stdout.strip():
            if account['version'] == 'v1':
                subprocess.run(['git', '-C', repo_dir, 'add', 'ami_refresh.tf'])
            elif account['version'] == 'v2':
                subprocess.run(['git', '-C', repo_dir, 'add', 'main.tf'])
            
            subprocess.run(['git', '-C', repo_dir, 'commit', '-m', commit_message], 
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,
                           check=True)
            subprocess.run(['git', '-C', repo_dir, 'push'], 
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,
                           check=True)
            
            print('\n' + '=' * 60 + '\n')
            print(f'• Pushed to Repo : {account['customer_name']} \n')
            print('=' * 60 + '\n')

        else:
            print(f'{account['customer_name'] + ':' :<45} --No Changes')
    except subprocess.CalledProcessError as e:
        print(f"Failed to push {account['customer_name']} to remote repository. Please resolve first.: {e}")
        exit (1)   # Make sure pipeline exits when a repo isn't pushed successfully

if base_folder.exists():
        os.chmod(base_folder, stat.S_IWRITE)
        shutil.rmtree(base_folder, onerror=remove_readonly)  # onerror = call remove_readonly function (Make it writable)


ado_username = input('Enter ADO username: ')
ado_password = getpass('Enter ADO password: ')
 
for account in masterfile:
    if not account['enabled']:
        continue
    else:
        profile_name = account['profile_name']
        session = authenticate_session(profile_name)
        get_lt()
        get_ami(session)
        clone_repo(account, ado_username, ado_password)
        print(f'{"Evision Launch Template:":25} {evision_lt[0]}')
        print(f'{"Stutalk Launch Template:":25} {stutalk_lt[0]}')
        print(f'{"AMI ID Used:":25} {ami_id}')

        if account['version'] == 'v1':
            repo_dir = Path(base_folder, edited_folder, account['repo_name'])
            update_ami_v1(ami_id, repo_dir, 'ami_refresh.tf')
        elif account['version'] == 'v2':
            repo_dir = Path(base_folder, edited_folder, account['repo_name'])
            update_ami_v2(ami_id, repo_dir, 'main.tf')

        repo_dir = Path(base_folder, edited_folder, account['repo_name'])
        logfile = Path(base_folder) / f'{formatted_date}-runlogs.txt'
        if not git_checks_porcelain():
            
            with open (logfile, 'a') as f:
                f.write('\n' + '=' * 60 + '\n')
                f.write(f'• Repo Name : {account['repo_name']} \n')
                f.write(f'• No Changes  \n')
                f.write('=' * 60 + '\n')
            continue
        else:
            output = change_validations()
            print(output)
            git_push()
            with open (logfile, 'a') as f:
                f.write('\n\n' + '=' * 60 + '\n')
                f.write(f'• Repo Name : {account['repo_name']} \n')
                f.write(f'• Changes Done :  \n')
                f.write('=' * 60 + '\n\n')
                f.write(output)

        # Clear the lists for another round of Account
        stutalk_lt.clear()
        evision_lt.clear()