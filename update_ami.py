import re
import os
from pathlib import Path
import json
import shutil

base_folder = 'repositories'
with open('repo_source.json') as f:
    source_file = json.load(f)

# Function for V1
def update_ami_v1(ami_id, repo_dir, target_file):
    with open(Path(base_folder, repo_dir, target_file), 'r') as file:
        content = file.read()
        
    pattern = r'(\s*default\s*=\s*")(ami-[^"]+)(")'
    replace = r'\1' + ami_id + r'\3'
    new_content = re.sub(pattern, replace, content)

    with open(Path(base_folder, repo_dir, target_file), 'w') as file:
        file.write(new_content)

#Function for V2
def update_ami_v2(ami_id, repo_dir, target_file):
    with open(Path(base_folder, repo_dir, target_file), 'r') as file:
        content = file.read()
        
    pattern1 = r'(evision_image_id\s*=\s*")(ami-[^"]+)(")' # [^"] = Match anything except whats inside the brackets
    pattern2 = r'(stutalk_image_id\s*=\s*")(ami-[^"]+)(")'
    replace = r'\1' + ami_id + r'\3'
    content2 = re.sub(pattern1, replace, content)
    final_content = re.sub(pattern2, replace, content2)

    with open(Path(base_folder, repo_dir, target_file), 'w') as file:
        file.write(final_content)

def backup(repo_name, target_file):
    backup_dir = 'backups'
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    if os.path.exists(Path(backup_dir) / repo_name):
        shutil.rmtree(Path(backup_dir) / repo_name)

    shutil.copytree(
    Path(base_folder) / repo_name,
    Path(backup_dir) / repo_name
)


for customer in source_file:
    
    if not customer['enabled']:
        continue
    else:
        backup(customer['customer_name'], customer['target_file'])
        if customer['version'] == 'v1':
            update_ami_v1(customer['deployment_ami_id'], customer['repo_dir'], customer['target_file'])
        elif customer['version'] == 'v2':
            update_ami_v2(customer['deployment_ami_id'], customer['repo_dir'], customer['target_file'])