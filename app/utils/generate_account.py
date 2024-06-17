import web3


def generate_web3_account():
    account = web3.Account.create()
    address = account.address
    private_key = account._private_key.hex()
    return address, private_key

