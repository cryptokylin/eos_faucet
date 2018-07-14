# eos_faucet

## server side:
```
cd your_working_dir

https://github.com/cryptokylin/eos_faucet.git

cd eos_fauce
```
open wallet.py, paste account (to create account, transfer tokens) name, wallet name, wallet password accordingly, then save

```
python clfaucet.py
```

## client side:

you can create at most 1000 accounts per day. 
```
create account: make request on http://13.125.53.113/create_account?<new_account_name>
```

you can get 100 tokens each call and max 1000 tokens per day. 
```
curl http://13.125.53.113/get_token?<your_account_name>
```
## note:

this code is for test purpose only, you should not use it on eos mainnet with your real account
