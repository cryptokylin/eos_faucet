

NODEOS_URL = "http://127.0.0.1:8888"              # testnet node api
KEOSD_URL = "http://localhost:8900"               # your keosd url

CHAIN_URL = ''.join([NODEOS_URL, "/v1/chain/"])
WALLET_URL = ''.join([KEOSD_URL, "/v1/wallet/"])

GET_INFO = ''.join([CHAIN_URL, "get_info"])
GET_BLOCK = ''.join([CHAIN_URL, "get_block"])
GET_BALANCE = ''.join([CHAIN_URL, "get_currency_balance"])
GET_ACCOUNT = ''.join([CHAIN_URL, "get_account"])
ABI_JSON_TO_BIN = ''.join([CHAIN_URL, "abi_json_to_bin"])
PUSH_TRANSACTION = ''.join([CHAIN_URL, "push_transaction"])

WALLET_SIGN_TRX = ''.join([WALLET_URL, "sign_transaction"])
WALLET_UNLOCK = ''.join([WALLET_URL, "unlock"])
WALLET_GET_PUBLIC_KEYS = ''.join([WALLET_URL, "get_public_keys"])
