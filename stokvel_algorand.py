import argparse
import json
import random
import time
from base64 import b64decode
from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod

# Algorand client initialization
ALGOD_ADDRESS = "https://testnet-api.algonode.cloud"
ALGOD_TOKEN = ""
algod_client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS)

def create_account():
    """Create a new Algorand account."""
    private_key, address = account.generate_account()
    mnemonic_phrase = mnemonic.from_private_key(private_key)
    return private_key, address, mnemonic_phrase

def load_participants(file_path):
    """Load participant data from a JSON file."""
    with open(file_path, 'r') as file:
        return json.load(file)

def send_transaction(mnemonic_phrase, receiver_address, amount, note=""):
    """Send ALGOs using a provided mnemonic."""
    private_key = mnemonic.to_private_key(mnemonic_phrase)
    sender_address = account.address_from_private_key(private_key)
    print(f"Sender Address: {sender_address}")

    params = algod_client.suggested_params()

    unsigned_txn = transaction.PaymentTxn(
        sender=sender_address,
        sp=params,
        receiver=receiver_address,
        amt=amount,
        note=note.encode('utf-8'),
    )

    signed_txn = unsigned_txn.sign(private_key)

    txid = algod_client.send_transaction(signed_txn)
    print(f"Transaction submitted with txID: {txid}")

    try:
        confirmed_txn = transaction.wait_for_confirmation(algod_client, txid, 4)
        print(f"Transaction confirmed in round {confirmed_txn['confirmed-round']}")
        print(f"Transaction information: {json.dumps(confirmed_txn, indent=4)}")
        if 'note' in confirmed_txn['txn']['txn']:
            print(f"Decoded note: {b64decode(confirmed_txn['txn']['txn']['note']).decode('utf-8')}")
    except Exception as e:
        print(f"Error during transaction confirmation: {e}")

def perform_monthly_cycle(participants):
    """Perform a monthly stokvel cycle."""
    amount = 500_000
    print("\nStokvel Participants:")
    for i, participant in enumerate(participants, start=1):
        print(f"Participant {i}:")
        print(f"  Address: {participant['address']}")
        print(f"  Mnemonic: {participant['mnemonic']}")

    msig = transaction.Multisig(1, 4, [p['address'] for p in participants])
    msig_address = msig.address()
    print(f"\nStokvel Multisig Address: {msig_address}")

    for participant in participants:
        addr = participant['address']
        mnem = participant['mnemonic']
        print(f"\n{addr} is sending {amount / 1_000_000} Algos to the multisig account.")
        send_transaction(mnem, msig_address, amount, note="Stokvel Contribution")
        time.sleep(5)

    unpaid_participants = [p for p in participants if not p.get('paid', False)]
    if not unpaid_participants:
        print("All participants have been paid. Resetting payment records.")
        for p in participants:
            p['paid'] = False
        unpaid_participants = participants

    recipient = random.choice(unpaid_participants)
    recipient_address = recipient['address']
    print(f"\nSelected recipient for this month: {recipient_address}")

    payout_amount = 2_000_000
    params = algod_client.suggested_params()
    payout_txn = transaction.PaymentTxn(
        sender=msig_address,
        sp=params,
        receiver=recipient_address,
        amt=payout_amount,
        note="Stokvel Payout".encode('utf-8'),
    )

    signed_txns = []
    for participant in participants:
        private_key = mnemonic.to_private_key(participant['mnemonic'])
        signed_txn = payout_txn.sign(private_key)
        signed_txns.append(signed_txn)
        print(f"Signature collected from {participant['address']}.")

        if len(signed_txns) >= 4:
            break

    if len(signed_txns) < 4:
        print("Not enough signatures collected for the payout transaction.")
    else:
        try:
            txid = algod_client.send_transactions(signed_txns)
            print(f"Payout transaction submitted with txID: {txid}")
            confirmed_txn = transaction.wait_for_confirmation(algod_client, txid, 4)
            print(f"Payout transaction confirmed in round {confirmed_txn['confirmed-round']}")
        except Exception as e:
            print(f"Error submitting payout transaction: {e}")

def main():
    parser = argparse.ArgumentParser(description="Algorand CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    stokvel_parser = subparsers.add_parser("stokvel", help="Run a monthly stokvel cycle")
    stokvel_parser.set_defaults(func=lambda args: perform_monthly_cycle(load_participants('stokvel_participants.json')))

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
