import boto3
import json
from auth import authenticate_session
import pprint

def get_asg(session):
    response = session.client('autoscaling').describe_auto_scaling_groups()
    
    for asg in response['AutoScalingGroups']:
        print(asg['LaunchTemplate']['LaunchTemplateId'])


# def get_ami():
#     with open('repo_source.json', 'r') as f:                                           # Grab the original file (w/ old AMI) 
#         source_file = json.load(f)
#         for account in source_file:
#             response = client.describe_instances(
#                 Filters=[
#                     {
#                         'Name': 'owner-id',
#                         'Values': [account['account_id']]
#                     }
#                 ],
#                 MaxResults=100
#             )
#             for reservation in response['Reservations']:
#                 for instance in reservation['Instances']:
#                     if instance['InstanceId'] == account['deployment_instance_id']:
#                         if instance['ImageId'] != account['deployment_ami_id']:
#                             account['enabled'] = True                             
#                             account['deployment_ami_id'] = instance['ImageId']
#                             print(f"ImageID of {account['customer_name'] + ':':<45}++Updated")
#                             print('*\n*')   
#                         elif instance['ImageId'] == account['deployment_ami_id']:
#                             account['enabled'] = False
#                             print(f"ImageID of {account['customer_name'] + ':':<45}--Skipped(current)")
#                             print('*\n*')
#                             continue

#     with open('repo_source.json', 'w') as f:                                           # Update the original file (w/ updated AMI)
#         json.dump(source_file, f, indent=1)

# get_ami()