import web3
from tronpy import Tron
from tronpy.keys import PrivateKey


def generate_erc20_account():
    account = web3.Account.create()
    address = account.address
    private_key = account._private_key.hex()
    return address, private_key


def generate_trc20_account():
    tron = Tron()

    # 生成新的私钥
    private_key = PrivateKey.random()
    # 获取账号地址
    accoun_address = private_key.public_key.to_base58check_address()

    return accoun_address, private_key
