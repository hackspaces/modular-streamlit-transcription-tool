

""" # Upload to S3 bucket 
def upload_to_s3(filename, bucketname):
    try:
        file_path = os.path.join('app/uploads', filename)
        s3_client.upload_file(file_path, bucketname, filename)
        return "Upload Successful", 200
    except FileNotFoundError:
        return "File not found", 404
    except NoCredentialsError:
        return "Credentials not available", 403 """