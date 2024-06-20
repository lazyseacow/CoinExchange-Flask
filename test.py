from app.auth.verify import sign_auth

symbol = 'BTC'
status = 'success'
operation_type = 'deposits'
page = 1
timestamp = 1718848332
encrypt_data = f'{symbol}+{status}+{operation_type}+{page}+{timestamp}'
sign = sign_auth.generate_signature(encrypt_data)
print(sign)
print(sign_auth.verify_signature(encrypt_data, timestamp, sign))
