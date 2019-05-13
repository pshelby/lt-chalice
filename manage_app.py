#!/usr/bin/env python

"""
Manage lifecycle for the Chalice service integration lightning talk.
"""

import argparse
import logging
import logging.config
from json import dump, dumps, loads
from subprocess import CalledProcessError, run

import yaml

import boto3
from botocore.exceptions import ClientError


def create_s3_bucket(args):
    """Create S3 bucket."""
    try:
        s3_client = boto3.client('s3')
        s3_client.create_bucket(Bucket=args.s3_bucket,
                                CreateBucketConfiguration={'LocationConstraint': args.region})
        logging.info('S3 bucket "%s" created', args.s3_bucket)
    except ClientError as err:
        if err.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            logging.info('S3 bucket "%s" already exists, and you own it.  Proceeding.',
                         args.s3_bucket)
        else:
            logging.error('Unable to create S3 bucket! %s', err.response['Error'])
            raise


def delete_s3_bucket(args):
    """Delete S3 bucket."""
    try:
        s3_resource = boto3.resource('s3')
        bucket = s3_resource.Bucket(args.s3_bucket)
        bucket.objects.all().delete()
        bucket.delete()
        logging.info('S3 bucket "%s" deleted', args.s3_bucket)
    except ClientError as err:
        if err.response['Error']['Code'] == 'NoSuchBucket':
            logging.info('S3 bucket "%s" does not exist.  Proceeding.', args.s3_bucket)
        else:
            logging.error('Unable to delete S3 bucket! %s', err.response['Error'])
            raise


def get_ssm_param_userid(client, args):
    """Retrieve SSM parameter."""
    user_id = 'lt-chalice-user'

    try:
        tag_list = client.list_tags_for_resource(ResourceType='Parameter',
                                                 ResourceId=args.phone_num_name)
        for tag in tag_list['TagList']:
            if tag['Key'] == 'CreatedBy':
                user_id = tag['Value']
    except ClientError as err:
        if err.response['Error']['Code'] != 'InvalidResourceId':
            logging.error('Unable to get SSM parameter tags! %s', err.response['Error'])

    return user_id


def get_current_user():
    """Return current user."""
    user = 'lt-chalice-user'

    try:
        sts_client = boto3.client('sts')
        user = sts_client.get_caller_identity()['UserId']
    except ClientError as err:
        logging.warning('Unable to retrieve current user.  Defaulting to "%s". %s',
                        user, err)

    return user


def create_ssm_param(args):
    """Create SSM parameter."""
    ssm_client = boto3.client('ssm')

    current_user = get_current_user()
    param_user = get_ssm_param_userid(ssm_client, args)

    try:
        ssm_client.put_parameter(Name=args.phone_num_name,
                                 Value=args.phone_num_value,
                                 Type='SecureString',
                                 Tags=[
                                     {
                                         "Key": "CreatedBy",
                                         "Value": current_user
                                     }
                                 ]
                                )
        logging.info('SSM parameter "%s" created', args.phone_num_name)
    except ClientError as err:
        if err.response['Error']['Code'] == 'ParameterAlreadyExists':
            if current_user == param_user:
                ssm_client.put_parameter(Name=args.phone_num_name,
                                         Value=args.phone_num_value,
                                         Type='SecureString',
                                         Overwrite=True
                                        )
                ssm_client.add_tags_to_resource(ResourceType='Parameter',
                                                ResourceId=args.phone_num_name,
                                                Tags=[
                                                    {
                                                        "Key": "CreatedBy",
                                                        "Value": current_user
                                                    }
                                                ]
                                               )
                logging.info('SSM parameter "%s" updated', args.phone_num_name)
        else:
            logging.error('Unable to create SSM parameter! %s', err.response['Error'])
            raise


def delete_ssm_param(args):
    """Delete SSM parameter."""
    ssm_client = boto3.client('ssm')

    current_user = get_current_user()
    param_user = get_ssm_param_userid(ssm_client, args)

    try:
        if current_user == param_user:
            ssm_client.delete_parameter(Name=args.phone_num_name)
            logging.info('SSM parameter "%s" deleted', args.phone_num_name)
        else:
            logging.warning('SSM parameter "%s" was not created by you!  Skipping.',
                            args.phone_num_name)
    except ClientError as err:
        if err.response['Error']['Code'] == 'ParameterNotFound':
            logging.info('SSM parameter "%s" does not exist.  Proceeding.', args.phone_num_name)
        else:
            logging.error('Unable to delete SSM parameter! %s', err.response['Error'])
            raise


def update_chalice_config(args, delete_flag=False):
    """Update config.json with values."""
    try:
        # Read config
        with open('{}/.chalice/config.json'.format(args.chalice_app_dir), 'r') as config_fh:
            config = loads(config_fh.read())
        logging.debug('Chalice config before: %s', dumps(config))

        # Add key
        if 'environment_variables' not in config:
            config['environment_variables'] = {}

        # Modify env vars
        if delete_flag:
            config['environment_variables']['PHONE_NUM_PARAM'] = ''
            config['environment_variables']['S3_BUCKET'] = ''
        else:
            config['environment_variables']['PHONE_NUM_PARAM'] = args.phone_num_name
            config['environment_variables']['S3_BUCKET'] = args.s3_bucket

        # Write config
        with open('{}/.chalice/config.json'.format(args.chalice_app_dir), 'w') as config_fh:
            dump(config, config_fh, indent="\t")
            config_fh.write('\n')
        logging.debug('Chalice config after: %s', dumps(config))
    except Exception as err:
        logging.error('Unable to update Chalice config! %s', err)
        raise


def chalice_command(args, action='deploy'):
    """Manage the Chalice app."""
    logging.debug('action: %s', action)
    try:
        cmd_object = run(["chalice", action], cwd=args.chalice_app_dir,
                         capture_output=True, text=True)
        cmd_object.check_returncode()
        logging.info('%s\n%s', action, cmd_object.stdout)
    except CalledProcessError as err:
        logging.error(cmd_object.stderr)
        logging.error(cmd_object.stdout)
        raise
    except Exception as err:
        logging.error('Unable to run Chalice command! %s', err)
        raise


def deploy(arguments):
    """Create resources required for Chalice demo."""
    logging.info('Deploying Chalice app...')
    create_s3_bucket(arguments)
    create_ssm_param(arguments)
    update_chalice_config(arguments)
    chalice_command(arguments)
    logging.info('Complete')


def delete(arguments):
    """Delete resources required for Chalice demo."""
    logging.info('Deleting Chalice app...')
    chalice_command(arguments, action='delete')
    update_chalice_config(arguments, delete_flag=True)
    delete_ssm_param(arguments)
    delete_s3_bucket(arguments)
    logging.info('Complete')


def parse_arguments():
    """Parse arguments."""
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--action', required=True, choices=['deploy', 'delete'],
                           help='deploy or delete')
    argparser.add_argument('--s3-bucket', required=True,
                           help='Name of S3 bucket for image uploads.')
    argparser.add_argument('--phone-number-parameter-name', required=True, dest='phone_num_name',
                           help='Full path of SSM parameter for phone number.  Remember to make \
                                   this as unique as possible (name spacing) to avoid global \
                                   conflicts.')
    argparser.add_argument('--phone-number-parameter-value', dest='phone_num_value',
                           help='Value of SSM parameter for phone number (Format "+XXXXXXXXXX").')
    argparser.add_argument('--chalice-app-dir', default='lt-chalice',
                           help='Directory of Chalice app to deploy (Default: "lt-chalice").')
    argparser.add_argument('--region', default='us-west-2',
                           help='Region in which to deploy resources (Default: "us-west-2").')
    return argparser.parse_args()


def setup_logging(path='.manage_app.logging_config.yml', level=logging.INFO):
    """Setup logging configuration."""
    try:
        with open(path, 'rt') as logging_f:
            config = yaml.safe_load(logging_f.read())
        logging.config.dictConfig(config)
    except (ValueError, TypeError, AttributeError, ImportError) as err:
        logging.basicConfig(level=level)
        logging.warning('Unable to use supplied logging config; continuing with basic logging. \
                %s', err)


if __name__ == '__main__':
    # Load logging config
    setup_logging()

    # Parse positional arguments
    ARGS = parse_arguments()

    # Call function corresopnding to action
    locals()[ARGS.action](ARGS)
