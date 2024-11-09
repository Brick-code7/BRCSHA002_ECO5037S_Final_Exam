import argparse
import json
from base64 import b64decode
from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod
import certifi
import os
import ssl

def send_transaction(mnemonic_phrase, receiver_address, amount, note=""):
    # Algonode TestNet endpoint
    algod_address = "https://testnet-api.algonode.cloud"
    algod_token = ""  # No token needed for Algonode

    # Create the algod client (without context, since not supported by AlgodClient)
    algod_client = algod.AlgodClient(algod_token, algod_address)

    # Convert mnemonic to private key
    private_key = mnemonic.to_private_key(mnemonic_phrase)
    sender_address = account.address_from_private_key(private_key)
    print(f"Sender Address: {sender_address}")

    # Fetch suggested network parameters
    params = algod_client.suggested_params()

    # Create a payment transaction
    unsigned_txn = transaction.PaymentTxn(
        sender=sender_address,
        sp=params,
        receiver=receiver_address,
        amt=amount,
        note=note.encode('utf-8'),
    )

    # Sign the transaction
    signed_txn = unsigned_txn.sign(private_key)

    # Submit the transaction
    txid = algod_client.send_transaction(signed_txn)
    print(f"Transaction submitted with txID: {txid}")

    # Wait for confirmation
    try:
        confirmed_txn = transaction.wait_for_confirmation(algod_client, txid, 4)
        print(f"Transaction confirmed in round {confirmed_txn['confirmed-round']}")
        print(f"Transaction information: {json.dumps(confirmed_txn, indent=4)}")
        if 'note' in confirmed_txn['txn']['txn']:
            print(f"Decoded note: {b64decode(confirmed_txn['txn']['txn']['note']).decode('utf-8')}")
    except Exception as e:
        print(f"Error during transaction confirmation: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send ALGOs using Algorand CLI")
    parser.add_argument("mnemonic_phrase", help="Mnemonic phrase for the sender account")
    parser.add_argument("receiver_address", help="Receiver's public address")
    parser.add_argument("amount", type=int, help="Amount of ALGOs to transfer (in microAlgos)")
    parser.add_argument("--note", default="", help="Optional note for the transaction")

    args = parser.parse_args()
    send_transaction(args.mnemonic_phrase, args.receiver_address, args.amount, args.note)
