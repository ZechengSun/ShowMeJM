"""
根据平台适配不同请求体
"""
from plugins.ShowMeJM.utils.jm_options import JmOptions

def get_headers(options: JmOptions):
    if options.token == "":
        headers = {
            'Content-Type': 'application/json'
        }
    else:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {options.token}'
        }
    return headers

# 获取群聊上传文件接口的请求体
def get_upload_group_file_request_body(options: JmOptions, group_id, file, name):
    if options.platform == 'napcat':
        url = f"http://{options.http_host}:{options.http_port}/upload_group_file"
        payload = {
            "group_id": group_id,
            "file": file,
            "name": name,
            "folder_id": options.group_folder
        }
    elif options.platform == 'llonebot':
        url = f"http://{options.http_host}:{options.http_port}/upload_group_file"
        payload = {
            "group_id": group_id,
            "file": file,
            "name": name,
            "folder_id": options.group_folder
        }
    elif options.platform == 'lagrange':
        url = f"http://{options.http_host}:{options.http_port}/upload_group_file"
        payload = {
            "group_id": group_id,
            "file": file,
            "name": name,
            "folder": options.group_folder
        }
    else:
        raise Exception("消息平台配置有误, 只能是'napcat', 'llonebot'或'lagrange'")
    headers = get_headers(options)
    return url, payload, headers

# 获取私聊上传文件的请求体
def get_upload_private_file_request_body(options: JmOptions, user_id, file, name):
    if options.platform == 'napcat':
        url = f"http://{options.http_host}:{options.http_port}/upload_private_file"
        payload = {
            "user_id": user_id,
            "file": file,
            "name": name
        }
    elif options.platform == 'llonebot':
        url = f"http://{options.http_host}:{options.http_port}/upload_private_file"
        payload = {
            "user_id": user_id,
            "file": file,
            "name": name
        }
    elif options.platform == 'lagrange':
        # lagrange上传私聊文件接口当前不可用 会报错
        url = f"http://{options.http_host}:{options.http_port}/upload_private_file"
        payload = {
            "user_id": user_id,
            "file": file,
            "name": name
        }
    else:
        raise Exception("消息平台配置有误, 只能是'napcat', 'llonebot'或'lagrange'")
    headers = get_headers(options)
    return url, payload, headers
