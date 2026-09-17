import requests

# URL of the upload endpoint
url = "http://172.17.0.1:15001/upload"

# Path to the file you want to upload
file_path = "/agent/agent_open_source/minio/b.txt"

# Open the file in binary mode and prepare the file payload
with open(file_path, "rb") as file:
    files = {"file": file}
    
    # Send the POST request to the upload endpoint
    response = requests.post(url, files=files)
    
    # Print the response from the server
    if response.status_code == 200:
        print("File uploaded successfully")
        print("Download link:", response.json()["download_link"])
    else:
        print("Failed to upload file")
        print("Error:", response.json())

