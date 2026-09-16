import requests

# URL of the upload endpoint
#url = "http://127.0.0.1:15002/upload"
url = "http://172.17.0.1:15002/upload"
data = {"formatted_markdown":'中文的1111111111111111111111111',"to_format":'docx',"title":'newdata'}

response = requests.post(url,data=data)
    
    # Print the response from the server
if response.status_code == 200:
    print("File uploaded successfully")
    print("Download link:", response.json()["download_link"])
else:
    print("Failed to upload file")
    print("Error:", response.json())

