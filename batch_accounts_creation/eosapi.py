
MAINNET_NODEOS_URL = "http://api.eos.store"
KYLIN_NODEOS_URL = "http://13.125.53.113:8888"
# KYLIN_NODEOS_URL = "http://127.0.0.1:8888"              # testnet node api
KEOSD_URL = "http://localhost:8900"               # your keosd url

MAINNET_CHAIN_URL = ''.join([MAINNET_NODEOS_URL, "/v1/chain/"])
KYLIN_CHAIN_URL = ''.join([KYLIN_NODEOS_URL, "/v1/chain/"])
WALLET_URL = ''.join([KEOSD_URL, "/v1/wallet/"])

MC_GET_ACCOUNT = ''.join([MAINNET_CHAIN_URL, "get_account"])

KC_GET_INFO = ''.join([KYLIN_CHAIN_URL, "get_info"])
KC_GET_BLOCK = ''.join([KYLIN_CHAIN_URL, "get_block"])
KC_GET_BALANCE = ''.join([KYLIN_CHAIN_URL, "get_currency_balance"])
KC_GET_ACCOUNT = ''.join([KYLIN_CHAIN_URL, "get_account"])
KC_ABI_JSON_TO_BIN = ''.join([KYLIN_CHAIN_URL, "abi_json_to_bin"])
KC_PUSH_TRANSACTION = ''.join([KYLIN_CHAIN_URL, "push_transaction"])

WALLET_SIGN_TRX = ''.join([WALLET_URL, "sign_transaction"])
WALLET_UNLOCK = ''.join([WALLET_URL, "unlock"])
WALLET_GET_PUBLIC_KEYS = ''.join([WALLET_URL, "get_public_keys"])
