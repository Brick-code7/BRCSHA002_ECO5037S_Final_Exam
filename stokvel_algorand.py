import json
import time
import random
from typing import List
from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod

# Algod Client Configuration
algod_address = "https://testnet-api.algonode.cloud"
algod_token = ""  # No token needed for public nodes like Algonode
algod_client = algod.AlgodClient(algod_token, algod_address)

# Load participants from a JSON file


participants = [
    {
        "mnemonic": "sign upon dolphin canoe peanut fatigue cry ghost trap scene nominee amount pilot tank segment demand require october still tape gospel kidney little absent there",
        "address": "HUYZ7Z2EN4OFYAVFQ5YNMMJTGWFWL4WRV7XKOJRKR2Z5HJTPHEQLQUJV4Y"
    },
    {
        "mnemonic": "cheese sunny rocket unaware hand word muffin gesture black bulk core kitchen depend earn funny eager next lobster daughter elevator bright cost club abstract frozen",
        "address": "MYEJQWW42QASN3SQPQABYAGRAPSB7JA3OPPH43EFXACEKE5Q2PSSLPUDVI"
    },
    {
        "mnemonic": "sound tackle mountain execute balcony room torch walnut bunker where choice next front actress length donate lazy quarter inherit seven average poem quiz abandon dinner",
        "address": "AXRJCK3MKKXKUMBLJN2XMATG52RBECMHBMB6IGLAQJCGOOOT7VY6MR7YUU"
    },
    {
        "mnemonic": "enemy receive tomato evoke tuna fatigue there rescue length poverty memory begin report draw click rocket spend lumber lazy top train know panda abandon achieve",
        "address": "5YTNUKJTTOQCIAUQIOMKM23KKRPGIHLPPF3ZKIPMUO4B5NFLEJNB3GR7SM"
    },
    {
        "mnemonic": "final light fury final oak apart eye runway walk cover fix window skirt wedding comic much used real vacant curious faith void chapter about fade",
        "address": "OTKYFQXLZNCQZSYOW3QITERLO3QHGA4A5OIII5HNWZWNNH2KJXZKWTRXYI"
    }
]

print("Stokvel Participants:")
for i, participant in enumerate(participants, start=1):
    print(f"Participant {i}:")
    print(f"  Address: {participant['address']}")
    print(f"  Mnemonic: {participant['mnemonic']}")

# Create a multisig account with a 4-of-5 threshold
msig = transaction.Multisig(1, 4, [p['address'] for p in participants])
msig_address = msig.address()
print(f"\nStokvel Multisig Address: {msig_address}")

def perform_payment_simulation_optimized(time_t: int):
    successful_payments = set()
    sum_amount = 0
    count_months = 1
    day = 1
    stop_simulation = False

    participants_addresses = [p['address'] for p in participants]
    participants_mnemonics = {p['address']: p['mnemonic'] for p in participants}  # Dictionary for quick lookup

    while not stop_simulation:
        print(f"This is day {day} of month {count_months}.")
        
        if day == time_t:  # Contribution day
            print(f"Day {day} of month {count_months} is contribution day.")
            sum_amount += process_contributions(participants_mnemonics, msig_address)

        if day == time_t + 1:  # Payout day
            print(f"Day {day} of month {count_months} is payout day.")
            recipient = select_random_unpaid_participant(participants_addresses, successful_payments)
            if recipient:
                perform_multisig_payout_optimized(msig_address, recipient, sum_amount * 0.6)
                successful_payments.add(recipient)
                sum_amount *= 0.4  # Remaining amount after payout

        # Reset or end condition logic
        if len(successful_payments) == len(participants):
            stop_simulation = handle_cycle_completion(successful_payments)

        # Increment and reset logic for months/days
        day, count_months = increment_day(day, count_months)

def process_contributions(participants_mnemonics, msig_address):
    amount = 100_000  # Contribution amount in microAlgos
    for address, mnem in participants_mnemonics.items():
        send_transaction(mnem, msig_address, amount, note="Stokvel Contribution")
    return amount * len(participants_mnemonics)

def select_random_unpaid_participant(participants_addresses, successful_payments):
    unpaid = [addr for addr in participants_addresses if addr not in successful_payments]
    return random.choice(unpaid) if unpaid else None

def perform_multisig_payout_optimized(sender, receiver, amount):
    params = algod_client.suggested_params()
    payout_txn = transaction.PaymentTxn(
        sender=sender,
        sp=params,
        receiver=receiver,
        amt=int(amount),  # Convert to integer if necessary
        note="Stokvel Payout".encode('utf-8'),
    )
    msig_payment_txn = transaction.MultisigTransaction(payout_txn, msig)
    signed_participants = 0
    for participant in participants:
        if input(f"Participant {participant['address']}, do you want to sign this transaction [y/n]") == 'y':
            signed_participants+=1
    
    if signed_participants>= 4:
        for participant in participants:
            private_key = mnemonic.to_private_key(participant['mnemonic'])
            msig_payment_txn.sign(private_key)

    try:
        txid = algod_client.send_transaction(msig_payment_txn)
        print(f"Payout transaction submitted with txID: {txid}")
        confirmed_txn = transaction.wait_for_confirmation(algod_client, txid, 4)
        print(f"Payout transaction confirmed in round {confirmed_txn['confirmed-round']}")
    except Exception as e:
        print(f"Error submitting payout transaction: {e}")

def handle_cycle_completion(successful_payments):
    for participant in participants:
        if input("Do you want to continue? (y/n): ").lower() == 'n':
            return True  # Stop simulation
    successful_payments.clear()
    return False

def increment_day(day, count_months):
    day += 1
    if day > 30:
        day = 1
        count_months += 1
        if count_months > 12:
            count_months = 1
    return day, count_months

def send_transaction(mnemonic_phrase, receiver_address, amount, note=""):
    private_key = mnemonic.to_private_key(mnemonic_phrase)
    sender_address = account.address_from_private_key(private_key)
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
    except Exception as e:
        print(f"Error during transaction confirmation: {e}")

if __name__ == "__main__":
    perform_payment_simulation_optimized(time_t=15)
