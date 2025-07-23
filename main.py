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
v1_filename = 'ami_refresh.tf'
v2_filename = 'main.tf'
stutalk_lt = []
evision_lt = []
ami_id = ''
ami_id_from_cloned_file = ''

############################ GETTING ASG's ##############################
def get_lt(account):
    auto_scaling = account.client('autoscaling').describe_auto_scaling_groups()
    for asg in auto_scaling['AutoScalingGroups']:
        if 'stutalk' in asg['LaunchTemplate']['LaunchTemplateName'].lower():
            stutalk_lt.append(asg['LaunchTemplate']['LaunchTemplateId'])
        elif 'evision' in asg['LaunchTemplate']['LaunchTemplateName'].lower():
            evision_lt.append((asg['LaunchTemplate']['LaunchTemplateId']))

########################## GETTING AMI ID's ##############################
def get_ami(account):
    lt_version = account.client('ec2').describe_launch_template_versions(
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

################## EXTRACTING AMI ID's CLONED FILE #########################

def extract_v1_ami(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    pattern = r'(\s*default\s*=\s*)(")(ami-)([a-zA-Z0-9]*)(")'
    match = re.search(pattern, content)
    if match:
        return match.group(3) + match.group(4)
    
def extract_v2_ami(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    pattern = r'(\s*evision_image_id\s*=\s*)(")(ami-)([a-zA-Z0-9]*)(")'
    match = re.search(pattern, content)
    if match:
        return match.group(3) + match.group(4)

########################## UPDATING AMI ID's #############################
# Function for V1
def update_ami_v1(file_path, ami):
    with open(file_path, 'r') as file:
        content = file.read()

    pattern = r'(\s*)(default)(\s*)(=)(\s*)(")([a-zA-Z-0-9]*)(")'
    replacement = rf'\1\2\3\4\5\6{ami}\8' 
    replaced_text = re.sub(pattern, replacement, content)
        
    with open(file_path, 'w') as file:
        file.write(replaced_text)

#Function for V2
def update_ami_v2(file_path, ami):
    with open(file_path, 'r') as file:
        content = file.read()

    evision_pattern = r'(\s*)(evision_image_id)(\s*)(=)(\s*)(")([a-zA-Z-0-9]*)(")'
    stutalk_pattern = r'(\s*)(stutalk_image_id)(\s*)(=)(\s*)(")([a-zA-Z-0-9]*)(")'
    evision_replacement = rf'\1\2\3\4\5\6{ami}\8'
    stutalk_replacement = rf'\1\2\3\4\5\6{ami}\8'
    final_content = re.sub(evision_pattern, evision_replacement, content)
    final_content = re.sub(stutalk_pattern, stutalk_replacement, final_content)

    with open(file_path, 'w') as file:
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
    print(result.stdout)
    return bool(result.stdout.strip())
    
def change_validations(file_path):
    result = subprocess.run(['git', '-C', file_path, 'diff'],
                    capture_output=True,
                    text=True
                    )
    return result.stdout

# def git_push(file_path, account, username, password):
#     repository_url = f"https://{username}:{password}@{account['repo_url']}"
#     try:
#         file_path = Path(base_folder, edited_folder, account['repo_name'])
#         commit_message = f"AMI Refresh Code Base Update - {formatted_date}"
        
#         result = subprocess.run(
#         ['git', '-C', file_path, 'status', '--porcelain'],
#         capture_output=True,
#         text=True
#     )
#         if result.stdout.strip():
#             if account['version'] == 'v1':
#                 subprocess.run(['git', '-C', file_path, 'add', v1_filename])
#             elif account['version'] == 'v2':
#                 subprocess.run(['git', '-C', file_path, 'add', v2_filename])
            
#             subprocess.run(['git', '-C', file_path, 'commit', '-m', commit_message], 
#                            stdout=subprocess.DEVNULL,
#                            stderr=subprocess.DEVNULL,
#                            check=True)
#             subprocess.run(['git', '-C', file_path, 'push'], 
#                            stdout=subprocess.DEVNULL,
#                            stderr=subprocess.DEVNULL,
#                            check=True)
            
#             print('\n' + '=' * 60 + '\n')
#             print(f'• Pushed to Repo : {account['customer_name']} \n')
#             print('=' * 60 + '\n')

#         # else:
#         #     print(f'{account['customer_name'] + ':' :<45} --No Changes')
#     except subprocess.CalledProcessError as e:
#         print(f"Failed to push {account['customer_name']} to remote repository. Please resolve first.: {e}")
#         exit (1)   # Make sure pipeline exits when a repo isn't pushed successfully

def clear_variables(var1, var2, var3, var4):
    var1.clear()
    var2.clear()
    var3 = ''
    var4 = ''

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
        get_lt(session)
        get_ami(session)
        clone_repo(account, ado_username, ado_password)
        print(f'{"Evision Launch Template:":35} {evision_lt[0]}')
        print(f'{"Stutalk Launch Template:":35} {stutalk_lt[0]}')
        print(f'{"AMI ID Used:":35} {ami_id}')

        repo_dir = Path(base_folder, edited_folder, account['repo_name'])
        logfile = Path(base_folder) / f'{formatted_date}-runlogs.txt'

        if account['version'] == 'v1':
            ami_id_from_cloned_file = extract_v1_ami(Path(repo_dir,v1_filename))
        elif account['version'] == 'v2':
            ami_id_from_cloned_file = extract_v2_ami(Path(repo_dir,v2_filename))

        print(f'{"Current AMI ID in codebase:":35} {ami_id_from_cloned_file}')

        if ami_id != ami_id_from_cloned_file:
            if account['version'] == 'v1':
                update_ami_v1(Path(repo_dir, v1_filename), ami_id)
                output = change_validations(repo_dir)
                print('\n')
                print(output)
            elif account['version'] == 'v2':
                # git_push(repo_dir, account, ado_username, ado_password)
                update_ami_v1(Path(repo_dir, v2_filename), ami_id)
            
            with open (logfile, 'a') as f:
                f.write('\n\n' + '=' * 60 + '\n')
                f.write(f'• Repo Name : {account['repo_name']} \n')
                f.write(f'• Changes Done :  \n')
                f.write('=' * 60 + '\n\n')
                f.write(output)
                    
                # Clear the lists for another round of Account
                clear_variables(stutalk_lt, evision_lt, ami_id, ami_id_from_cloned_file)
        else:
            print("There are no changes. Please see logfile.")
            with open (logfile, 'a') as f:
                f.write('\n' + '=' * 60 + '\n')
                f.write(f'• Repo Name : {account['repo_name']} \n')
                f.write(f'• No Changes  \n')
                f.write('=' * 60 + '\n')
            # Clear the lists for another round of Account
            clear_variables(stutalk_lt, evision_lt, ami_id, ami_id_from_cloned_file)
            continue
            