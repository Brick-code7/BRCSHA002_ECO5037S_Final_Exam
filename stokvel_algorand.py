import json
import time
import random
from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod

# Algod Client Configuration
algod_address = "https://testnet-api.algonode.cloud"
algod_token = ""  # No token needed for public nodes like Algonode
algod_client = algod.AlgodClient(algod_token, algod_address)

# Load participants from a JSON file (or configure directly)
def load_participants(file_path='stokvel_participants.json'):
    with open(file_path, 'r') as file:
        return json.load(file)

participants = load_participants()

print("Stokvel Participants:")
for i, participant in enumerate(participants, start=1):
    print(f"Participant {i}:")
    print(f"  Address: {participant['address']}")
    print(f"  Mnemonic: {participant['mnemonic']}")

# Create a multisig account with a 4-of-5 threshold
msig = transaction.Multisig(1, 4, [p['address'] for p in participants])
msig_address = msig.address()
print(f"\nStokvel Multisig Address: {msig_address}")

# Function to perform monthly cycle
def perform_monthly_cycle():
    amount = 100_000  # 0.5 Algos in microAlgos

    for participant in participants:
        addr = participant['address']
        mnem = participant['mnemonic']
        print(f"\n{addr} is sending {amount / 1_000_000} Algos to the multisig account.")
        send_transaction(mnem, msig_address, amount, note="Stokvel Contribution")
        time.sleep(5)  # Wait for transaction confirmation

    # Select a random recipient who hasn't been paid yet
    unpaid_participants = [p for p in participants if not p.get('paid', False)]
    if not unpaid_participants:
        print("All participants have been paid. Resetting payment records.")
        for p in participants:
            p['paid'] = False
        unpaid_participants = participants

    recipient = random.choice(unpaid_participants)
    recipient_address = recipient['address']
    print(f"\nSelected recipient for this month: {recipient_address}")

    # Prepare the payout transaction
    payout_amount = 300_000  # 2 Algos in microAlgos
    params = algod_client.suggested_params()
    payout_txn = transaction.PaymentTxn(
        sender=msig_address,
        sp=params,
        receiver=recipient_address,
        amt=payout_amount,
        note="Stokvel Payout".encode('utf-8'),
    )
    msig_payment_txn = transaction.MultisigTransaction(payout_txn, msig)
    signed_txns = []
    for participant in participants:
        private_key = mnemonic.to_private_key(participant['mnemonic'])
        msig_payment_txn.sign(private_key)

        #if len(signed_txns) >= 4:
            #break

    # Submit the multisig transaction
    try:
        #signed_txn = signed_txns.finalize()
        txid = algod_client.send_transaction(msig_payment_txn)
        print(f"Payout transaction submitted with txID: {txid}")
        confirmed_txn = transaction.wait_for_confirmation(algod_client, txid, 4)
        print(f"Payout transaction confirmed in round {confirmed_txn['confirmed-round']}")
    except Exception as e:
        print(f"Error submitting payout transaction: {e}")

def send_transaction(mnemonic_phrase, receiver_address, amount, note=""):
    # Convert mnemonic to private key
    private_key = mnemonic.to_private_key(mnemonic_phrase)
    sender_address = account.address_from_private_key(private_key)

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
    except Exception as e:
        print(f"Error during transaction confirmation: {e}")

if __name__ == "__main__":
    perform_monthly_cycle()
