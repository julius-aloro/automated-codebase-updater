import json
import subprocess
import os

with open('repo_source.json') as f:
    source_file = json.load(f)

base_folder = 'repositories'
if not os.path.exists(base_folder):
    os.mkdir(base_folder)

def clone_repo():
    for account in source_file:
        if not account['enabled']:
            continue
        else:
            repo_url = account['repo_url']
            try:
                subprocess.run(["git", '-C', base_folder, "clone", "--quiet", repo_url],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                check=True) # Hide Output
                
                print(f"Clone {account['customer_name'] + ' in local repository:':<45}  ++Successful")
                print('*\n*')
                
            except subprocess.CalledProcessError as e:
                print(f"Failed to clone {account['customer_name']} repository. Please resolve manually: {e}")
                exit (1)   # Make sure pipeline exits when a repo isn't cloned successfully

clone_repo()