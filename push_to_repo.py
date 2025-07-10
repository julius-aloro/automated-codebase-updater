from pathlib import Path
import subprocess
from datetime import datetime
import json

formatted_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
base_dir = 'repositories'

with open('repo_source.json') as f:
    source_file = json.load(f)

def change_validations(account):
    repo_dir = Path(base_dir, account['repo_dir'])
    diff_result = subprocess.run(['git', '-C', str(repo_dir), 'diff'],
                                 capture_output=True,
                                 text=True
                                 )

    print(f"Changes in {account['customer_name']}:")
    print('*\n*')
    print("#" * 60)
    print("#" * 60)
    print(diff_result.stdout)

    


def git_push(account):
    try:
        repo_dir = Path(base_dir, account['repo_dir'])
        commit_message = f"AMI Refresh Code Base Update (Weekly Pipeline Run) - {formatted_date}"
        
        result = subprocess.run(
        ['git', '-C', str(repo_dir), 'status', '--porcelain'],
        capture_output=True,
        text=True
    )
        if result.stdout.strip():
            
            change_validations(account)     # Do a diff for manual checks

            if account['version'] == 'v1':
                subprocess.run(['git', '-C', str(repo_dir), 'add', 'ami_refresh.tf'])
            elif account['version'] == 'v2':
                subprocess.run(['git', '-C', str(repo_dir), 'add', 'main.tf'])
            
            subprocess.run(['git', '-C', str(repo_dir), 'commit', '-m', str(commit_message) ], 
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,
                           check=True)
            subprocess.run(['git', '-C', str(repo_dir), 'push'], 
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,
                           check=True)
            
            print(f"Push {account['customer_name'] + 'to remote repository:':<45} ++Successful")
            print('*\n*')

        else:
            print(f'{account['customer_name'] + ':' :<45} --No Changes')
    except subprocess.CalledProcessError as e:
        print(f"Failed to push {account['customer_name']} to remote repository. Please resolve first.: {e}")
        exit (1)   # Make sure pipeline exits when a repo isn't pushed successfully

for account in source_file:
    
    if account['enabled'] == True:
        git_push(account)
