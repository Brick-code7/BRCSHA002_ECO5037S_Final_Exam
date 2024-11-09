import json
from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod
import random
import time
from transfer_algo import send_transaction  # Import the function

# Initialize the Algod client
algod_address = "https://testnet-api.algonode.cloud"
algod_token = ""  # No token needed for Algonode
algod_client = algod.AlgodClient(algod_token, algod_address)

# Load participants from the JSON file
def load_participants(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

participants = load_participants('stokvel_participants.json')

print("Stokvel Participants:")
for i, participant in enumerate(participants, start=1):
    print(f"Participant {i}:")
    print(f"  Address: {participant['address']}")
    print(f"  Mnemonic: {participant['mnemonic']}")

# Create a multisig account with a 4-of-5 threshold
msig = transaction.Multisig(1, 4, [p['address'] for p in participants])
msig_address = msig.address()
print(f"\nStokvel Multisig Address: {msig_address}")

# Function to perform a monthly cycle
def perform_monthly_cycle():
    amount = 500_000  # 0.5 Algos in microAlgos
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
    payout_amount = 2_000_000  # 2 Algos in microAlgos
    params = algod_client.suggested_params()
    payout_txn = transaction.PaymentTxn(
        sender=msig_address,
        sp=params,
        receiver=recipient_address,
        amt=payout_amount,
        note="Stokvel Payout".encode('utf-8'),
    )

    # Collect signatures from 4 out of 5 participants
    signed_txns = []
    for participant in participants:
        private_key = mnemonic.to_private_key(participant['mnemonic'])
        
        # Sign the payout transaction
        signed_txn = payout_txn.sign(private_key)
        signed_txns.append(signed_txn)
        
        print(f"Signature collected from {participant['address']}.")

        # Check if we have enough signatures
        if len(signed_txns) >= 4:
            break

    # Ensure we have the required number of signatures
    if len(signed_txns) < 4:
        print("Not enough signatures collected for the payout transaction.")
    else:
        # Create a group transaction
        group_id = transaction.calculate_group_id(signed_txns)
        for txn in signed_txns:
            txn.group = group_id

        # Submit the signed transaction
        try:
            txid = algod_client.send_transactions(signed_txns)
            print(f"Payout transaction submitted with txID: {txid}")
            confirmed_txn = transaction.wait_for_confirmation(algod_client, txid, 4)
            print(f"Payout transaction confirmed in round {confirmed_txn['confirmed-round']}")
        except Exception as e:
            print(f"Error submitting payout transaction: {e}")

# Run the monthly cycle
perform_monthly_cycle()
