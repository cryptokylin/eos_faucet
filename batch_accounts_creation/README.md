# batch accounts creation

```
cd your_working_dir

https://github.com/cryptokylin/eos_faucet.git

cd eos_faucet/batch_accounts_creation
```
open wallet.py, paste account (to create account, transfer tokens) name, wallet name, wallet password accordingly, then save and run
the following script to launch the processes of bac.py

```
python bac.py &
```
It can take long time to run, in case of lost of terminal connection, use following to check the progress or stop the bac.py processes.
```
python ctl.py progress|stop
```
