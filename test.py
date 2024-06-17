import requests
from PIL import Image
import qrcode
import io

# 配置
url = 'http://192.168.1.10:5000/bindwallet'
token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6dHJ1ZSwiaWF0IjoxNzE4MzU3MzQ5LCJqdGkiOiJlMmUzNWFiZC0wNWNkLTQ1MGItYTQ2ZC05NTAwZWVkYjk1MzUiLCJ0eXBlIjoiYWNjZXNzIiwic3ViIjoxMywibmJmIjoxNzE4MzU3MzQ5LCJjc3JmIjoiNjg4ODJhYWQtM2RkZi00ZmE2LWJkYjAtYWEwNzRmZjQyYmYwIiwiZXhwIjoxNzE4NDQzNzQ5fQ.W78f-eEMr9-X1fCoNUDqqVw14jyv5WrC9t5XQYIMf5M'  # 替换为实际的JWT token
headers = {
    'Authorization': f'Bearer {token}'
}

# 模拟二维码图片生成
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4,
)
wallet_address = '4na4ui78mh4o84w4omjye489498i99q78wfdasfdaf'  # 替换为实际的wallet address
qr.add_data(wallet_address)
qr.make(fit=True)

img = qr.make_image(fill='black', back_color='white')
img_byte_arr = io.BytesIO()
img.save(img_byte_arr, format='PNG')
img_byte_arr.seek(0)
# 保存二维码图片
with open('wallet_qr.png', 'wb') as f:
    f.write(img_byte_arr.getvalue())

print("二维码图片已保存为 'wallet_qr.png'")

# # 模拟POST请求
# data = {
#     'currency': 'BTC',
#     'agreement_type': 'ERC20',
#     'wallet_address': wallet_address,
#     'comment': 'Test wallet binding'
# }
# files = {
#     'wallet_qr': ('qr.png', img_byte_arr, 'image/png')
# }

# response = requests.post(url, headers=headers, data=data, files=files)
#
# # 打印响应结果
# print(response.status_code)
# try:
#     print(response.json())
# except requests.exceptions.JSONDecodeError:
#     print(response.text)
