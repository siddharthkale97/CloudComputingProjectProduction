import os
from flask import Flask, flash, request, redirect, url_for, render_template
from werkzeug.utils import secure_filename
# import sys
import boto3
import json
from decouple import config
from timeit import default_timer as timer

RESPONSE_QUEUE_NAME = 'responsequeue.fifo'
REQUEST_QUEUE_NAME = 'requestqueue.fifo'
INPUT_BUCKET = 'inputbucketskale9'

# sys.path.append('D:\Codes\CloudComputingProject1\TestProject1\classifier')

# from image_classification import *

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# sqs = boto3.resource('sqs', region_name='us-east-1',
#         aws_access_key_id=config('ACCESS_ID'),
#         aws_secret_access_key=config('ACCESS_KEY'))

#test code
sqs = boto3.client('sqs', 
                    region_name='us-east-1', 
                    aws_access_key_id=config('ACCESS_ID'),
                    aws_secret_access_key= config('ACCESS_KEY'))
# test code ends
# queue = sqs.get_queue_by_name(QueueName=RESPONSE_QUEUE_NAME)

app = Flask(__name__)
app.config["Debug"] = True
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_filename(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/get_res/<total_files>', methods=['GET'])
def get_res(total_files=None):
    # Only for testing
    if total_files == None or int(total_files)<=0:
        total_files = 3
    else:
        total_files = int(total_files)
    # Only for testing!!
    return render_template("uploaded_successfully.html", total_files=total_files)

@app.route('/show_res/<total_files>', methods=['GET'])
def show_res_now(total_files=None):
    # Below 2 lines are just for testing!
    if total_files == None or int(total_files)<=0:
        total_files = 4
    
    total_files = int(total_files)
    results = []
    print("total files = ", total_files)
    # test code here
    response = sqs.get_queue_url(QueueName=RESPONSE_QUEUE_NAME)
    queue_url = str(response['QueueUrl'])
    start_time = timer()
    end_time = timer()
    while (len(results)<int(total_files)):
        if (abs(end_time-start_time)>=120):
            break
        response = sqs.receive_message(
            QueueUrl=queue_url,
            AttributeNames=[
                'SentTimestamp'
            ],
            MaxNumberOfMessages=1,
            MessageAttributeNames=[
                'All'
            ],
            VisibilityTimeout=180,
            WaitTimeSeconds=0
        )

        if 'Messages' in response:
            message = response['Messages'][0]
            receipt_handle = message['ReceiptHandle']
            print(message)

            sqs.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=message['ReceiptHandle']
            )
            print('Received and deleted message: %s' % message)
            message_body = json.loads(message['Body'])
            results.append(message_body)
            print("result is ",results)
            print("len of results is ", len(results))

        end_time = timer()
        # print(end_time-start_time)
    print("out")
    print("results are =>  ")
    print(results)
    return render_template("show_result.html", results=results)

# Previous code for directly returning the result
@app.route('/', methods=['GET', 'POST'])
def upload_file():
   if request.method == 'POST':
        files = request.files.getlist("file[]")
        total_files = len(files)
        # if 'file' not in request.files:
        #     flash('No file part')
        #     return redirect(request.url)
        # file = request.files['file']
        # print(files)
        results = []
        for file in files:
            if file.filename == "":
                flash('No selected file')
                return redirect(request.url)
            if file and allowed_filename(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                print(path)
                try:
                    upload_file_to_bucket(path, INPUT_BUCKET)
                except:
                    return "error has occurred" 
                # Delete the file in located at path variable!!
        return redirect(url_for('get_res', total_files = total_files))
        # if file.filename == "":
        #     flash('No selected file')
        #     return redirect(request.url)
        # if file and allowed_filename(file.filename):
        #     filename = secure_filename(file.filename)
        #     file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        #     path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        #     print(path)
        #     result = evaluate_image(path)
        #     return result
        #     #return redirect(url_for('uploaded_file', filename = filename))
   return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name="file[]" multiple="">
      <input type=submit value=Upload>
    </form>
    '''
def upload_file_to_bucket(file_name, bucket):
    object_name = file_name
    s3_client = boto3.client('s3',
                region_name='us-east-1',
                aws_access_key_id=config('ACCESS_KEY'),
                aws_secret_access_key=config('SECRET_KEY')
    )
    response = s3_client.upload_file(file_name, bucket, object_name)

    sqs = boto3.client('sqs',
                region_name='us-east-1',
                aws_access_key_id=config('ACCESS_KEY'),
                aws_secret_access_key=config('SECRET_KEY')
    )
    sqs_request = sqs.get_queue_url(QueueName=REQUEST_QUEUE_NAME)
    request_queue_url = str(sqs_request['QueueUrl'])
    # message = queue.send_message(MessageBody=file_name, MessageGroupId='1')
    sqs.send_message(
                QueueUrl=request_queue_url,
                MessageBody=str(file_name),
                MessageGroupId='1'
            )
    return response

app.run()