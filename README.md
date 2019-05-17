# lt-chalice-service-integrations
This app will spin up a Lambda function via AWS Chalice, which watches the provided S3 bucket for upload events.  If an image is uploaded to the bucket, the Lambda function will use AWS Rekognition to detect any faces that may exist in the image.  Then, if faces are detected, it will send a text message to the phone number provided.

## Setup

For this demo you'll need:
* Python3.7 virtual env
* `pip install -r requirements.txt`

## Usage

```bash
usage: manage_app.py [-h] --action {deploy,delete} --s3-bucket S3_BUCKET
                     --phone-number-parameter-name PHONE_NUM_NAME
                     [--phone-number-parameter-value PHONE_NUM_VALUE]
                     [--chalice-app-dir CHALICE_APP_DIR] [--region REGION]

optional arguments:
  -h, --help            show this help message and exit
  --action {deploy,delete}
                        deploy or delete
  --s3-bucket S3_BUCKET
                        Name of S3 bucket for image uploads.
  --phone-number-parameter-name PHONE_NUM_NAME
                        Full path of SSM parameter for phone number. Remember
                        to make this as unique as possible (name spacing) to
                        avoid global conflicts.
  --phone-number-parameter-value PHONE_NUM_VALUE
                        Value of SSM parameter for phone number (Format
                        "+XXXXXXXXXX").
  --chalice-app-dir CHALICE_APP_DIR
                        Directory of Chalice app to deploy (Default: "lt-
                        chalice").
  --region REGION       Region in which to deploy resources (Default: "us-
                        west-2").
```

## Running

The `manage-app.py` script will handle all prerequisite setup and deployment of the Chalice app for you.  Simply supply the required arguments with the `deploy` action.

```bash
% ./manage_app.py --action deploy --s3-bucket pshelby-lt-chalice-west --phone-number-parameter-name /lt-chalice/pshelby/phone-num --phone-number-parameter-value +1XXXXXXXXXX --chalice-app-dir ./lt-chalice
2019-05-17 09:53:57,213 - INFO - deploy - Deploying Chalice app...
2019-05-17 09:53:58,772 - INFO - create_s3_bucket - S3 bucket "pshelby-lt-chalice-west" created
2019-05-17 09:54:00,209 - INFO - create_ssm_param - SSM parameter "/lt-chalice/pshelby/phone-num" created
2019-05-17 09:54:14,664 - INFO - chalice_command - deploy
Creating deployment package.
Creating IAM role: lt-chalice-dev-image_upload_handler
Creating lambda function: lt-chalice-dev-image_upload_handler
Configuring S3 events in bucket pshelby-lt-chalice-west to function lt-chalice-dev-image_upload_handler
Resources deployed:
  - Lambda ARN: arn:aws:lambda:us-west-2:XXXXXXXXXXXX:function:lt-chalice-dev-image_upload_handler

2019-05-17 09:54:14,664 - INFO - deploy - Complete
%
```

## Testing

Upload an image (preferrably with a face in it) to your S3 bucket, and you should receive a text message telling you about the face.

`aws s3 cp /image1.jpg s3://your-s3-bucket`

## Cleaning up

`manage-app.py` script also handles cleanup after execution is complete.  Pass required args with the `--delete` action.

```bash
% ./manage_app.py --action delete --s3-bucket pshelby-lt-chalice-west --phone-number-parameter-name /lt-chalice/pshelby/phone-num --chalice-app-dir ./lt-chalice
2019-05-01 14:03:34,210 - INFO - delete - Deleting Chalice app...
2019-05-01 14:03:37,089 - INFO - chalice_command - delete
Deleting function: arn:aws:lambda:us-west-2:XXXXXXXXXXXX:function:lt-chalice-dev-recognize_faces
Deleting IAM role: lt-chalice-dev-recognize_faces

2019-05-01 14:03:38,294 - INFO - delete_ssm_param - SSM parameter "/lt-chalice/pshelby/phone-num" deleted
2019-05-01 14:03:40,016 - INFO - delete_s3_bucket - S3 bucket "pshelby-lt-chalice-west" deleted
2019-05-01 14:03:40,018 - INFO - delete - Complete
%
```
