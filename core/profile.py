import boto3
import botocore

def profile_get_aws_account(profile, boto_session):
    try:
        #Get info about the account for that profile format the same as SSO
        ident = boto_session.client('sts').get_caller_identity()
        pag = boto_session.client('iam').get_paginator('list_account_aliases')
        
        try:
            for response in pag.paginate():
                # Just grab the first alias so there is something to reference the account
                aname = response['AccountAliases'][0]
                break
        # If no aliases use the account ID
        except: 
            aname = ident['Account']

        account = {'accountId':ident['Account'],'accountName':aname}
        return account

    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'AccessDenied':
            print(
                f"\tProfile {profile} does not have permissions to get account info...trying next profile")