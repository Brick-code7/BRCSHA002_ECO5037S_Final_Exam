# generate_account.py
from algosdk import account, encoding, mnemonic

def create_account():
    private_key, address = account.generate_account()
    mnemonic_phrase = mnemonic.from_private_key(private_key)
    return private_key, address, mnemonic_phrase

    
if __name__ == "__main__":
    pk, addr, mnem = create_account()
    print(f"Address: {addr}")
    print(f"Private Key: {pk}")
    print(f"Mnemonic: {mnem}")