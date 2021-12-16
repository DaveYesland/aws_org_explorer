import boto3
import botocore
import sys

from core.sso import retrieve_aws_sso_token, retrieve_aws_accounts, retrieve_credentials, retrieve_roles_in_account
from core.profile import profile_get_aws_account
from core.iamEnum import retreive_roles, retreive_users
from core.db import Db

import concurrent.futures

from config import neo4j_config, sso_config


def get_token_from_cache():
    try:
        with open("token", 'r') as f:
            return f.readline()
    except FileNotFoundError:
        return None


def save_token_to_cache(token):
    with open("token", 'w') as f:
        f.write(token)


def sso_process_account(sso, aws_sso_token, account, db):

    sso_roles = retrieve_roles_in_account(sso, aws_sso_token, account)

    # Loop through roles. If role get permission error on list, try next.
    for access_role in sso_roles:

        print(f"\tListing {account['accountId']} using role, {access_role}")

        aws_access_key_id, aws_secret_access_key, aws_session_token = retrieve_credentials(
            sso, aws_sso_token, account['accountId'], access_role)

        iamClient = boto3.client('iam', aws_access_key_id=aws_access_key_id,
                                 aws_secret_access_key=aws_secret_access_key,
                                 aws_session_token=aws_session_token)
        try:
            roles = retreive_roles(iamClient)
            users = retreive_users(iamClient)
            
            for role in roles:
                db.add_aws_role(role)
            for user in users:
                db.add_aws_user(user)

            # If no exceptions were had break this loop and start next account
            break

        except botocore.exceptions.ClientError as error:
            if error.response['Error']['Code'] == 'AccessDenied':
                print(
                    f"\tRole {access_role} does not have permissions to list users/roles...trying next role")
                continue

def profile_process_account(profile, boto_session, account, db):    
    try:
        print(f"\tListing {account['accountId']} using profile, {profile}")
        iamClient = boto_session.client('iam')
        roles = retreive_roles(iamClient)
        users = retreive_users(iamClient)
        
        for role in roles:
            db.add_aws_role(role)
        for user in users:
            db.add_aws_user(user)

    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'AccessDenied':
            print(
                f"\tProfile {profile} does not have permissions to list users/roles...trying next role")

if __name__ == "__main__":
    db = Db(neo4j_config['host'], neo4j_config['user'], neo4j_config['pass'])
    

    if len(sys.argv) > 1:
        profiles = sys.argv[1:]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            count = 0
            for profile in profiles:
                boto_session = boto3.session.Session(profile_name=profile)
                account = profile_get_aws_account(profile, boto_session)
                db.add_aws_account(account)
                futures.append(executor.submit(
                    profile_process_account, profile, boto_session, account, db))
            
            
            for future in concurrent.futures.as_completed(futures):
                count += 1
                print(f"Completed ({count}/{len(profiles)})")
    else:
        aws_sso_token = get_token_from_cache()
        sso = boto3.client('sso', region_name=sso_config['region'])

        try:
            aws_accounts_list = retrieve_aws_accounts(sso, aws_sso_token)
        except Exception as error:
            aws_sso_token = retrieve_aws_sso_token(None)
            save_token_to_cache(aws_sso_token)
            aws_accounts_list = retrieve_aws_accounts(sso, aws_sso_token)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            count = 0
            for account in aws_accounts_list:
                db.add_aws_account(account)
                futures.append(executor.submit(
                    sso_process_account, sso, aws_sso_token, account, db))


            for future in concurrent.futures.as_completed(futures):
                count += 1
                print(f"Completed ({count}/{len(aws_accounts_list)})")
