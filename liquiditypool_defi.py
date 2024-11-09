from algosdk import mnemonic
from algosdk.v2client import algod
from algosdk.transaction import AssetConfigTxn, AssetTransferTxn, PaymentTxn

# Algorand connection and utility functions
algod_address = "https://testnet-api.algonode.cloud"
algod_token = ""
client = algod.AlgodClient(algod_token, algod_address)

def wait_for_confirmation(client, txid):
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
    params = client.suggested_params()
    txn = AssetConfigTxn(
        sender=sender_address,
        sp=params,
        total=1000000,
        decimals=2,
        default_frozen=False,
        unit_name="UCTZAR",
        asset_name="UCTZAR Stablecoin",
        manager=sender_address,
        reserve=sender_address,
        freeze=sender_address,
        clawback=sender_address
    )
    signed_txn = txn.sign(sender_private_key)
    txid = client.send_transaction(signed_txn)
    wait_for_confirmation(client, txid)
    ptx = client.pending_transaction_info(txid)
    asset_id = ptx["asset-index"]
    print(f"Created UCTZAR ASA with ID: {asset_id}")
    return asset_id

def opt_in_to_asa(account_private_key, account_address, asset_id):
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

# Liquidity Pool Class (same as before)
class LiquidityPool:
    def __init__(self):
        self.algo_reserves = 0
        self.uctzar_reserves = 0
        self.liquidity_providers = {}
        self.total_liquidity_tokens = 0

    def add_liquidity(self, provider_address, algo_amount, uctzar_amount):
        if self.total_liquidity_tokens == 0:
            liquidity_tokens = algo_amount + uctzar_amount
        else:
            liquidity_tokens = int((algo_amount + uctzar_amount) / (self.algo_reserves + self.uctzar_reserves) * self.total_liquidity_tokens)

        self.algo_reserves += algo_amount
        self.uctzar_reserves += uctzar_amount
        self.total_liquidity_tokens += liquidity_tokens

        self.liquidity_providers[provider_address] = {
            "algo_amount": algo_amount,
            "uctzar_amount": uctzar_amount,
            "liquidity_tokens": liquidity_tokens
        }
        print(f"{provider_address} added liquidity: {algo_amount} ALGOs, {uctzar_amount} UCTZARs and received {liquidity_tokens} liquidity tokens.")

    def swap_algo_for_uctzar(self, trader_address, algo_amount):
        fee_percentage = 0.003
        fee = algo_amount * fee_percentage
        net_algo_amount = algo_amount - fee

        uctzar_amount = (self.uctzar_reserves * net_algo_amount) / (self.algo_reserves + net_algo_amount)
        
        self.algo_reserves += net_algo_amount
        self.uctzar_reserves -= uctzar_amount

        self.distribute_fees(fee, asset='algo')
        print(f"{trader_address} swapped {algo_amount} ALGOs for {uctzar_amount} UCTZARs and paid {fee} ALGOs in fees.")

    def swap_uctzar_for_algo(self, trader_address, uctzar_amount):
        fee_percentage = 0.003
        fee = uctzar_amount * fee_percentage
        net_uctzar_amount = uctzar_amount - fee

        algo_amount = (self.algo_reserves * net_uctzar_amount) / (self.uctzar_reserves + net_uctzar_amount)
        
        self.uctzar_reserves += net_uctzar_amount
        self.algo_reserves -= algo_amount

        self.distribute_fees(fee, asset='uctzar')
        print(f"{trader_address} swapped {uctzar_amount} UCTZARs for {algo_amount} ALGOs and paid {fee} UCTZARs in fees.")

    def distribute_fees(self, fee, asset='algo'):
        for provider_address, provider_data in self.liquidity_providers.items():
            provider_share = provider_data['liquidity_tokens'] / self.total_liquidity_tokens
            fee_share = fee * provider_share
            if asset == 'algo':
                provider_data['algo_amount'] += fee_share
            else:
                provider_data['uctzar_amount'] += fee_share
            print(f"Distributed {fee_share} {asset.upper()}s in fees to {provider_address}.")

    def withdraw_liquidity(self, provider_address):
        if provider_address not in self.liquidity_providers:
            print(f"{provider_address} is not a liquidity provider.")
            return
        provider_data = self.liquidity_providers.pop(provider_address)
        liquidity_tokens = provider_data['liquidity_tokens']
        algo_amount = (liquidity_tokens / self.total_liquidity_tokens) * self.algo_reserves
        uctzar_amount = (liquidity_tokens / self.total_liquidity_tokens) * self.uctzar_reserves

        self.algo_reserves -= algo_amount
        self.uctzar_reserves -= uctzar_amount
        self.total_liquidity_tokens -= liquidity_tokens

        print(f"{provider_address} withdrew {algo_amount} ALGOs and {uctzar_amount} UCTZARs.")

# Main Program Execution
if __name__ == "__main__":
    # Use your specific funded accounts
    private_key1 = "i9F8En+dx3vQgqwhnvvDpLG10pGJCTPlVwNkZefAqP7xXrGfNELzcNDQx4n8nX6k+cMTTtcI1sCQ5NfLmOHwkQ=="
    address1 = "6FPLDHZUILZXBUGQY6E7ZHL6UT44GE2O24ENNQEQ4TL4XGHB6CIS33DLL4"
    private_key2 = "LEZEYhpiSKeW/ncWoxdXXYyQYUndZVB15/9BoHqISS7UIBF/84446PHkdDhW6SukFKhTaNRLqWMFl8fudvIpqA=="
    address2 = "2QQBC77TRY4OR4PEOQ4FN2JLUQKKQU3I2RF2SYYFS7D645XSFGUN5XSTXA"

    # Additional accounts
    private_key3 = "ksirSMt5RFxobDUCS8DbuPYcN0ramL0DU/aWCtJQ4H9eJ3nohpdkS8XvsffCimhz95Mdr0LRWhXASaqp2gEA9g=="
    address3 = "LYTXT2EGS5SEXRPPWH34FCTIOP3ZGHNPILIVUFOAJGVKTWQBAD3H2MZSEI"
    private_key4 = "ymRiGIU6nBE2sbzyzXD1YzvTRkg/I1GKmg3k3JAy59tsFa0Y2K/EruUIztziyKeQzdIm0jkPlyoPTUMotrkLLg=="
    address4 = "NQK22GGYV7CK5ZIIZ3OOFSFHSDG5EJWSHEHZOKQPJVBSRNVZBMXPUWWZ7U"

    # Liquidity providers and traders
    liquidity_providers = [
        {'private_key': private_key1, 'address': address1},
        {'private_key': private_key2, 'address': address2}
    ]
    traders = [
        {'private_key': private_key3, 'address': address3},
        {'private_key': private_key4, 'address': address4}
    ]

    # Ensure accounts are funded (already funded as per your message)

    # Create UCTZAR ASA using the first liquidity provider
    uctzar_id = create_uctzar_asa(liquidity_providers[0]['private_key'], liquidity_providers[0]['address'])

    # Opt-in to ASA for all accounts
    for provider in liquidity_providers:
        opt_in_to_asa(provider['private_key'], provider['address'], uctzar_id)

    for trader in traders:
        opt_in_to_asa(trader['private_key'], trader['address'], uctzar_id)

    # Initialize Liquidity Pool
    pool = LiquidityPool()

    # Providers add liquidity
    pool.add_liquidity(liquidity_providers[0]['address'], 1000, 2000)
    pool.add_liquidity(liquidity_providers[1]['address'], 500, 1000)
    # Traders perform swaps
    pool.swap_algo_for_uctzar(traders[0]['address'], 100)
    pool.swap_uctzar_for_algo(traders[1]['address'], 200)

    # Providers withdraw liquidity
    for provider in liquidity_providers:
        pool.withdraw_liquidity(provider['address'])
