import requests

# https://catbox.moe/
CATBOX_API = 'https://catbox.moe/user/api.php'

def upload(file_or_url: str) ->str:
    '''Upload an File to Catbox
        by uploading a file or by using an Url.'''
    
    if file_or_url.startswith('https://') or file_or_url.startswith('http://'):
        return url_upload(file_or_url)
    else:
        return file_upload(file_or_url)
    
def file_upload(file_path: str):
    data={
        'reqtype':'fileupload',
    }  
    
    with open(file_path, 'rb') as f:
        files = {'fileToUpload' : f}
        response = requests.post(CATBOX_API, data=data, files=files, verify=False)
    
    if response.status_code==200:
        return response.text.strip()
    else:
        raise Exception(f'Failed to Upload File: {response.status_code} {response.text}')
        
def url_upload(file_url: str) -> str:
    data = {
        "reqtype": "urlupload",
        "url": file_url,
    }

    response = requests.post(CATBOX_API, data=data, verify=False)
    if response.status_code == 200:
        return response.text.strip()
    else:
        raise Exception(f"URL upload failed: {response.status_code} {response.text}")