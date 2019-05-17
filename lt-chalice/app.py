"""
App to 'rekognize' faces in images uploaded to an S3 bucket.
"""

import json
from logging import INFO
from os import environ

import boto3
from botocore.exceptions import ClientError
from chalice import Chalice

app = Chalice(app_name='lt-chalice') # pylint: disable=C0103
app.log.setLevel(INFO)

PHONE_NUM_PARAM = environ['PHONE_NUM_PARAM']
S3_BUCKET = environ['S3_BUCKET']

@app.on_s3_event(bucket=S3_BUCKET, events=['s3:ObjectCreated:*'])
def image_upload_handler(event):
    """Handle image upload events from S3 bucket."""
    send_notification(recognize_faces(event))


def recognize_faces(event):
    """
    #Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
    #PDX-License-Identifier: MIT-0 (For details, see
    https://github.com/awsdocs/amazon-rekognition-developer-guide/blob/master/LICENSE-SAMPLECODE.)
    """

    result = []

    try:
        rek_client = boto3.client('rekognition')

        response = rek_client.detect_faces(Image={'S3Object':{'Bucket':event.bucket, \
                'Name':event.key}}, Attributes=['ALL'])

        app.log.info('Detected %d face(s) for %s', len(response['FaceDetails']), event.key)
        for face_detail in response['FaceDetails']:
            app.log.info('The detected face is between %s and %s years old',
                         face_detail['AgeRange']['Low'], face_detail['AgeRange']['High'])
            app.log.debug('Here are the other attributes:')
            app.log.debug(json.dumps(face_detail, indent=4, sort_keys=True))

        result = response['FaceDetails']

    except ClientError as err:
        app.log.error('Unable to run face detection! %s', err)

    return result


def send_notification(face_details):
    """Send a text to a phone number."""

    result = {}

    try:
        ssm_client = boto3.client('ssm')
        ssm_response = ssm_client.get_parameter(Name=PHONE_NUM_PARAM, WithDecryption=True)
        phone_num = ssm_response['Parameter']['Value']
    except ClientError as err:
        app.log.error('Unable to retreive phone number! %s', err)
        return result

    try:
        sns_client = boto3.client('sns')

        for face_detail in face_details:
            message_text = 'The detected face is between {} and {} years old'.format(\
                    face_detail['AgeRange']['Low'], face_detail['AgeRange']['High'])
            result = sns_client.publish(Message=message_text, PhoneNumber=phone_num)
    except ClientError as err:
        app.log.error('Unable to send notification! %s', err)

    return result
