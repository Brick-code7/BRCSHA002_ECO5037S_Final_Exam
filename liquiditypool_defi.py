from algosdk import mnemonic
from algosdk.v2client import algod
from algosdk.transaction import (
    AssetConfigTxn, AssetTransferTxn, PaymentTxn,
    calculate_group_id
)
from algosdk.account import generate_account

# Algorand connection and utility functions
algod_address = "https://testnet-api.algonode.cloud"
algod_token = ""
client = algod.AlgodClient(algod_token, algod_address)

def wait_for_confirmation(client, txid):
    """Utility function to wait for a transaction to be confirmed."""
    last_round = client.status().get('last-round')
    while True:
        txinfo = client.pending_transaction_info(txid)
        if txinfo.get('confirmed-round', 0) > 0:
            print(f"Transaction {txid} confirmed in round {txinfo.get('confirmed-round')}.")
            break
        else:
            print("Waiting for confirmation...")
            last_round += 1
            client.status_after_block(last_round)

def create_uctzar_asa(sender_private_key, sender_address):
    """Creates the UCTZAR ASA (Algorand Standard Asset)."""
    params = client.suggested_params()
    txn = AssetConfigTxn(
        sender=sender_address,
        sp=params,
        total=1_000_000,  # Total supply
        decimals=2,
        default_frozen=False,
        unit_name="UCTZAR",
        asset_name="UCTZAR Stablecoin",
        manager=sender_address,
        reserve=sender_address,
        freeze=sender_address,
        clawback=sender_address,
        strict_empty_address_check=False
    )

    signed_txn = txn.sign(sender_private_key)
    txid = client.send_transaction(signed_txn)
    wait_for_confirmation(client, txid)
    ptx = client.pending_transaction_info(txid)
    asset_id = ptx["asset-index"]
    print(f"Created UCTZAR ASA with ID: {asset_id}")
    return asset_id

def opt_in_to_asa(account_private_key, account_address, asset_id):
    """Opts an account into an ASA to be able to receive it."""
    params = client.suggested_params()
    txn = AssetTransferTxn(
        sender=account_address,
        sp=params,
        receiver=account_address,
        amt=0,
        index=asset_id
    )
    signed_txn = txn.sign(account_private_key)
    txid = client.send_transaction(signed_txn)
    wait_for_confirmation(client, txid)
    print(f"Account {account_address} opted-in to ASA {asset_id}.")

def distribute_uctzar(sender_private_key, sender_address, recipient_address, amount):
    """Distributes UCTZAR tokens from the creator to other accounts."""
    params = client.suggested_params()
    txn = AssetTransferTxn(
        sender=sender_address,
        receiver=recipient_address,
        amt=int(amount * 100),  # UCTZAR has decimals=2
        index=uctzar_id,
        sp=params
    )
    signed_txn = txn.sign(sender_private_key)
    txid = client.send_transaction(signed_txn)
    wait_for_confirmation(client, txid)
    print(f"Sent {amount} UCTZARs from {sender_address} to {recipient_address}.")

def check_balance(address):
    """Checks the ALGO balance of an account."""
    account_info = client.account_info(address)
    balance = account_info.get('amount') / 1_000_000  # Convert from microAlgos to ALGOs
    print(f"Account {address} has a balance of {balance} ALGOs.")

def check_uctzar_balance(address):
    """Checks the UCTZAR balance of an account."""
    account_info = client.account_info(address)
    for asset in account_info.get('assets', []):
        if asset['asset-id'] == uctzar_id:
            balance = asset['amount'] / 100  # Convert from base units
            print(f"Account {address} has a UCTZAR balance of {balance}.")
            return
    print(f"Account {address} has no UCTZAR balance.")

# Liquidity Pool Class with internal LPTOKEN management
class LiquidityPool:
    def __init__(self, liquidity_pool_address, liquidity_pool_private_key):
        self.algo_reserves = 0
        self.uctzar_reserves = 0
        self.total_liquidity_tokens = 0
        self.liquidity_providers = {}  # Tracks each provider's liquidity tokens
        self.liquidity_pool_address = liquidity_pool_address
        self.liquidity_pool_private_key = liquidity_pool_private_key

    def calculate_liquidity_tokens(self, algo_amount, uctzar_amount):
        if self.total_liquidity_tokens == 0:
            # Initial liquidity tokens
            return int((algo_amount + uctzar_amount) * 1000)  # Multiply to avoid very small numbers
        else:
            # Proportional calculation based on existing reserves
            total_pool_value = self.algo_reserves + self.uctzar_reserves
            added_value = algo_amount + uctzar_amount
            return int((added_value / total_pool_value) * self.total_liquidity_tokens)

    def add_liquidity(self, provider_private_key, provider_address, algo_amount, uctzar_amount):
        global uctzar_id  # Assuming this is defined elsewhere
        # Prepare transactions
        params = client.suggested_params()

        # Transaction 1: Provider sends ALGOs to liquidity pool
        txn1 = PaymentTxn(
            sender=provider_address,
            receiver=self.liquidity_pool_address,
            amt=int(algo_amount * 1_000_000),  # Correct conversion
            sp=params
        )

        # Transaction 2: Provider sends UCTZAR to liquidity pool
        txn2 = AssetTransferTxn(
            sender=provider_address,
            receiver=self.liquidity_pool_address,
            amt=int(uctzar_amount * 100),  # UCTZAR has decimals=2
            index=uctzar_id,
            sp=params
        )

        # Group transactions
        gid = calculate_group_id([txn1, txn2])
        txn1.group = gid
        txn2.group = gid

        # Sign transactions
        stxn1 = txn1.sign(provider_private_key)
        stxn2 = txn2.sign(provider_private_key)

        # Submit transactions
        signed_group = [stxn1, stxn2]
        txid = client.send_transactions(signed_group)
        wait_for_confirmation(client, txid)

        # Calculate and distribute liquidity tokens
        liquidity_tokens = self.calculate_liquidity_tokens(algo_amount, uctzar_amount)
        self.total_liquidity_tokens += liquidity_tokens
        self.algo_reserves += algo_amount
        self.uctzar_reserves += uctzar_amount

        # Update provider's liquidity token balance
        if provider_address in self.liquidity_providers:
            self.liquidity_providers[provider_address] += liquidity_tokens
        else:
            self.liquidity_providers[provider_address] = liquidity_tokens

        print(f"{provider_address} added liquidity: {algo_amount} ALGOs, {uctzar_amount} UCTZARs and received {liquidity_tokens} liquidity tokens.")

    def swap_algo_for_uctzar(self, trader_private_key, trader_address, algo_amount):
        global uctzar_id
        fee_percentage = 0.003
        fee = algo_amount * fee_percentage
        net_algo_amount = algo_amount - fee

        # Calculate UCTZAR amount using constant product formula
        k = self.algo_reserves * self.uctzar_reserves
        new_algo_reserves = self.algo_reserves + net_algo_amount
        new_uctzar_reserves = k / new_algo_reserves
        uctzar_amount = self.uctzar_reserves - new_uctzar_reserves

        # Ensure that pool has enough UCTZAR to fulfill the swap
        if uctzar_amount > self.uctzar_reserves:
            print("Not enough UCTZAR in reserves to complete the swap.")
            return

        # Prepare transactions
        params = client.suggested_params()

        # Transaction 1: Trader sends ALGOs to liquidity pool
        txn1 = PaymentTxn(
            sender=trader_address,
            receiver=self.liquidity_pool_address,
            amt=int(algo_amount * 1_000_000),
            sp=params
        )

        # Transaction 2: Liquidity pool sends UCTZAR to trader
        txn2 = AssetTransferTxn(
            sender=self.liquidity_pool_address,
            receiver=trader_address,
            amt=int(uctzar_amount * 100),
            index=uctzar_id,
            sp=params
        )

        # Group transactions
        gid = calculate_group_id([txn1, txn2])
        txn1.group = gid
        txn2.group = gid

        # Sign transactions
        stxn1 = txn1.sign(trader_private_key)
        stxn2 = txn2.sign(self.liquidity_pool_private_key)

        # Submit transactions
        signed_group = [stxn1, stxn2]
        txid = client.send_transactions(signed_group)
        wait_for_confirmation(client, txid)

        # Update reserves
        self.algo_reserves += net_algo_amount
        self.uctzar_reserves -= uctzar_amount

        # Add fee to pool reserves
        self.algo_reserves += fee

        print(f"{trader_address} swapped {algo_amount} ALGOs for {uctzar_amount} UCTZARs and paid {fee} ALGOs in fees.")

    def swap_uctzar_for_algo(self, trader_private_key, trader_address, uctzar_amount):
        global uctzar_id
        fee_percentage = 0.003
        fee = uctzar_amount * fee_percentage
        net_uctzar_amount = uctzar_amount - fee

        # Calculate ALGO amount using constant product formula
        k = self.algo_reserves * self.uctzar_reserves
        new_uctzar_reserves = self.uctzar_reserves + net_uctzar_amount
        new_algo_reserves = k / new_uctzar_reserves
        algo_amount = self.algo_reserves - new_algo_reserves

        # Ensure that pool has enough ALGO to fulfill the swap
        if algo_amount > self.algo_reserves:
            print("Not enough ALGO in reserves to complete the swap.")
            return

        # Prepare transactions
        params = client.suggested_params()

        # Transaction 1: Trader sends UCTZAR to liquidity pool
        txn1 = AssetTransferTxn(
            sender=trader_address,
            receiver=self.liquidity_pool_address,
            amt=int(uctzar_amount * 100),
            index=uctzar_id,
            sp=params
        )

        # Transaction 2: Liquidity pool sends ALGOs to trader
        txn2 = PaymentTxn(
            sender=self.liquidity_pool_address,
            receiver=trader_address,
            amt=int(algo_amount * 1_000_000),
            sp=params
        )

        # Group transactions
        gid = calculate_group_id([txn1, txn2])
        txn1.group = gid
        txn2.group = gid

        # Sign transactions
        stxn1 = txn1.sign(trader_private_key)
        stxn2 = txn2.sign(self.liquidity_pool_private_key)

        # Submit transactions
        signed_group = [stxn1, stxn2]
        txid = client.send_transactions(signed_group)
        wait_for_confirmation(client, txid)

        # Update reserves
        self.uctzar_reserves += net_uctzar_amount
        self.algo_reserves -= algo_amount

        # Add fee to pool reserves
        self.uctzar_reserves += fee

        print(f"{trader_address} swapped {uctzar_amount} UCTZARs for {algo_amount} ALGOs and paid {fee} UCTZARs in fees.")

    def withdraw_liquidity(self, provider_private_key, provider_address):
        if provider_address not in self.liquidity_providers or self.liquidity_providers[provider_address] == 0:
            print(f"{provider_address} has no liquidity tokens.")
            return

        # Calculate provider's share
        liquidity_tokens = self.liquidity_providers[provider_address]
        share = liquidity_tokens / self.total_liquidity_tokens

        # Calculate amounts to return
        algo_amount = self.algo_reserves * share
        uctzar_amount = self.uctzar_reserves * share

        # Prepare transactions
        params = client.suggested_params()

        # Transaction 1: Liquidity pool sends ALGOs back to provider
        txn1 = PaymentTxn(
            sender=self.liquidity_pool_address,
            receiver=provider_address,
            amt=int(algo_amount * 1_000_000),
            sp=params
        )

        # Transaction 2: Liquidity pool sends UCTZARs back to provider
        txn2 = AssetTransferTxn(
            sender=self.liquidity_pool_address,
            receiver=provider_address,
            amt=int(uctzar_amount * 100),
            index=uctzar_id,
            sp=params
        )

        # Group transactions
        gid = calculate_group_id([txn1, txn2])
        txn1.group = gid
        txn2.group = gid

        # Sign transactions
        stxn1 = txn1.sign(self.liquidity_pool_private_key)
        stxn2 = txn2.sign(self.liquidity_pool_private_key)

        # Submit transactions
        signed_group = [stxn1, stxn2]
        txid = client.send_transactions(signed_group)
        wait_for_confirmation(client, txid)

        # Update reserves and provider's liquidity tokens
        self.algo_reserves -= algo_amount
        self.uctzar_reserves -= uctzar_amount
        self.total_liquidity_tokens -= liquidity_tokens
        self.liquidity_providers[provider_address] = 0

        print(f"{provider_address} withdrew {algo_amount} ALGOs and {uctzar_amount} UCTZARs.")

# Main Program Execution
if __name__ == "__main__":
    # Replace with your own testnet accounts and private keys
    # Ensure these accounts are funded via the Algorand Testnet Dispenser

    # Liquidity Provider Accounts
    private_key1 = "i9F8En+dx3vQgqwhnvvDpLG10pGJCTPlVwNkZefAqP7xXrGfNELzcNDQx4n8nX6k+cMTTtcI1sCQ5NfLmOHwkQ=="
    address1 = "6FPLDHZUILZXBUGQY6E7ZHL6UT44GE2O24ENNQEQ4TL4XGHB6CIS33DLL4"
    private_key2 = "LEZEYhpiSKeW/ncWoxdXXYyQYUndZVB15/9BoHqISS7UIBF/84446PHkdDhW6SukFKhTaNRLqWMFl8fudvIpqA=="
    address2 = "2QQBC77TRY4OR4PEOQ4FN2JLUQKKQU3I2RF2SYYFS7D645XSFGUN5XSTXA"

    # Trader Accounts
    private_key3 = "ksirSMt5RFxobDUCS8DbuPYcN0ramL0DU/aWCtJQ4H9eJ3nohpdkS8XvsffCimhz95Mdr0LRWhXASaqp2gEA9g=="
    address3 = "LYTXT2EGS5SEXRPPWH34FCTIOP3ZGHNPILIVUFOAJGVKTWQBAD3H2MZSEI"
    private_key4 = "ymRiGIU6nBE2sbzyzXD1YzvTRkg/I1GKmg3k3JAy59tsFa0Y2K/EruUIztziyKeQzdIm0jkPlyoPTUMotrkLLg=="
    address4 = "NQK22GGYV7CK5ZIIZ3OOFSFHSDG5EJWSHEHZOKQPJVBSRNVZBMXPUWWZ7U"

    # Liquidity Pool Account
    liquidity_pool_private_key = "FgaLwmWp+iHILCDNt/LVwRgHkOHMxySGFPYO6EFFvX23zhqlf/Dntu5zglU2zwPQkoGZWjGyCuDjVR8y2wh66Q=="
    liquidity_pool_address = "W7HBVJL76DT3N3TTQJKTNTYD2CJIDGK2GGZAVYHDKUPTFWYIPLU23P6JTA"

    # Liquidity providers and traders
    liquidity_providers = [
        {'private_key': private_key1, 'address': address1},
        {'private_key': private_key2, 'address': address2}
    ]
    traders = [
        {'private_key': private_key3, 'address': address3},
        {'private_key': private_key4, 'address': address4}
    ]

    # Check balances before transactions
    print("Initial Balances:")
    for account in liquidity_providers + traders:
        check_balance(account['address'])
    check_balance(liquidity_pool_address)

    # Create UCTZAR ASA using the first liquidity provider
    uctzar_id = create_uctzar_asa(liquidity_providers[0]['private_key'], liquidity_providers[0]['address'])

    # Opt-in to UCTZAR for all accounts
    for account in liquidity_providers + traders:
        opt_in_to_asa(account['private_key'], account['address'], uctzar_id)

    # Liquidity pool account opts in to UCTZAR
    opt_in_to_asa(liquidity_pool_private_key, liquidity_pool_address, uctzar_id)

    # Distribute UCTZARs to other accounts
    print("\nDistributing UCTZARs to other accounts...")
    for account in liquidity_providers[1:] + traders:
        distribute_uctzar(
            liquidity_providers[0]['private_key'],
            liquidity_providers[0]['address'],
            account['address'],
            10  # Adjust the amount as needed
        )

    # Check UCTZAR balances
    print("\nUCTZAR Balances After Distribution:")
    for account in liquidity_providers + traders:
        check_uctzar_balance(account['address'])

    # Initialize Liquidity Pool
    pool = LiquidityPool(liquidity_pool_address, liquidity_pool_private_key)

    # Providers add liquidity with adjusted amounts
    pool.add_liquidity(liquidity_providers[0]['private_key'], liquidity_providers[0]['address'], 2, 4)
    pool.add_liquidity(liquidity_providers[1]['private_key'], liquidity_providers[1]['address'], 1, 2)

    # Check balances after adding liquidity
    print("\nBalances after adding liquidity:")
    for account in liquidity_providers + traders:
        check_balance(account['address'])
    check_balance(liquidity_pool_address)

    # Traders perform swaps with smaller amounts
    pool.swap_algo_for_uctzar(traders[0]['private_key'], traders[0]['address'], 0.5)
    pool.swap_uctzar_for_algo(traders[1]['private_key'], traders[1]['address'], 1)

    # Check balances after swaps
    print("\nBalances after swaps:")
    for account in liquidity_providers + traders:
        check_balance(account['address'])
    check_balance(liquidity_pool_address)

    # Providers withdraw liquidity
    for provider in liquidity_providers:
        pool.withdraw_liquidity(provider['private_key'], provider['address'])

    # Check final balances
    print("\nFinal Balances:")
    for account in liquidity_providers + traders:
        check_balance(account['address'])
    check_balance(liquidity_pool_address)
