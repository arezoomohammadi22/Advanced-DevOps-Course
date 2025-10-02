import os
import boto3
from flask import Flask, request

app = Flask(__name__)

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    endpoint_url=os.environ["AWS_ENDPOINT"],
)

bucket = os.environ["AWS_BUCKET"]

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    s3.upload_fileobj(file, bucket, file.filename)
    return f"Uploaded {file.filename} to bucket {bucket}\\n"

@app.route("/list", methods=["GET"])
def list_files():
    objects = s3.list_objects_v2(Bucket=bucket)
    if "Contents" not in objects:
        return "Bucket empty\\n"
    return "\\n".join(obj["Key"] for obj in objects["Contents"]) + "\\n"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
