import multiprocessing as mp
import pandas as pd
import os
# import sys
import time
import json
import requests

import eosapi
import wallet
import re

def kc_account_exists(account_name):
  payload = json.dumps({'account_name': account_name})
  response = requests.request("POST", eosapi.KC_GET_ACCOUNT, data=payload)
  if response.status_code == 200:
    ret = json.loads(response.text)
    return ret['account_name'] == account_name
  else:
    return False

def kc_account_cpu_available(account_name):
  payload = json.dumps({'account_name': account_name})
  response = requests.request("POST", eosapi.KC_GET_ACCOUNT, data=payload)
  if response.status_code == 200:
    ret = json.loads(response.text)
    return ret['cpu_limit']['available']
  else:
    return 0

def is_supported_newaccount_name(account_name):
  return len(account_name) == 12 and not re.search(r'[^a-z1-5]', account_name)

def unlock_wallet():
  param = json.dumps([
    wallet.NAME,
    wallet.PASSWD
  ])
  response = requests.request("POST", eosapi.WALLET_UNLOCK, data=param)
  return response.status_code == 200

def is_wallet_locked():
  response = requests.request("POST", eosapi.WALLET_GET_PUBLIC_KEYS)
  return response.status_code != 200

def unlock_wallet_if_locked():
  unlocked = False
  if is_wallet_locked():
    unlocked = unlock_wallet()
  else:
    unlocked = True
  return unlocked

def assembly_args(account_name, owner_key, active_key):
  p = {
    'creator':        wallet.ACCOUNT,
    'account':        account_name,
    'owner_key':      owner_key,
    'active_key':     active_key,
    'stake-cpu':      '1 EOS',
    'stake-net':      '1 EOS',
    'buy-ram-kbytes': 8
  }
  return p

tps_limit_sleep_time = 0.2                 # 0.2 second
cpu_available_wait_threshold = 60000000    # 60 second
cpu_available_wait_time = 3                # 3 second

def os_cmd_kc_create_account(nodeos_url, p):
  if not wait_if_account_cpu_not_available(p['creator']):
    return False
  cmdline = 'cleos --url {} system newaccount --stake-net \'{}\' --stake-cpu \'{}\' --buy-ram-kbytes {} {} {} {} {}'.format(
    nodeos_url,
    p['stake-net'],
    p['stake-cpu'],
    p['buy-ram-kbytes'],
    p['creator'],
    p['account'],
    p['owner_key'],
    p['active_key']
  )
  result = os.system(cmdline)
  return result == 0

def wait_if_account_cpu_not_available(account):
  available = kc_account_cpu_available(account)
  while available < cpu_available_wait_threshold:
    if has_global_stop_signal():
      return False
    time.sleep(cpu_available_wait_time)
    available = kc_account_cpu_available(account)
  return True

def os_cmd_kc_transfer(from_account, to_account, quantity, symbol, memo):
  if not wait_if_account_cpu_not_available(from_account):
    return False
  cmdline = 'cleos --url {} transfer {} {} "{} {}" "{}"'.format(eosapi.KYLIN_NODEOS_URL,
                                                                from_account,
                                                                to_account,
                                                                quantity,
                                                                symbol,
                                                                memo)
  result = os.system(cmdline)
  return result == 0

def kc_create_account_from_mc_account(kc_nodeos_url, name):
  if not is_supported_newaccount_name(name):
    ret = {'status': 'fail', 'msg': 'unsupported creation'}
    return ret

  if kc_account_exists(name):
    ret = {'status': 'fail', 'msg': 'exists already'}
    return ret

  mc_keys = mc_get_account_keys(name)
  if mc_keys and mc_keys['owner'] and mc_keys['active']:
    p = assembly_args(name, mc_keys['owner'], mc_keys['active'])
    if not unlock_wallet_if_locked():
      ret = {'status': 'fail', 'msg': 'failed to createa account, unlock wallet failed'}
      return ret
    if os_cmd_kc_create_account(kc_nodeos_url, p):
      time.sleep(tps_limit_sleep_time) # sleep to reduce the tps
      if os_cmd_kc_transfer(wallet.ACCOUNT, name, 10, 'EOS', 'try Crypto Kylin Testnet'):
        time.sleep(tps_limit_sleep_time) # sleep to reduce the tps
        ret = {'status': 'done', 'msg':'succeeded'}
      else:
        ret = {'status': 'done', 'msg':'account creation succeeded, but token transfer failed or stopped'}
    else:
      ret = {'status': 'fail', 'msg': 'cmd line creation failed or stopped'}
  else:
    ret = {'status': 'fail', 'msg': 'keys not found on mainnet'}

  return ret

def mc_get_account_keys(account_name):
  payload = json.dumps({'account_name': account_name})
  response = requests.request("POST", eosapi.MC_GET_ACCOUNT, data=payload)
  if response.status_code == 200:
    ret = json.loads(response.text)
    owner_key = None
    active_key = None
    for p in ret['permissions']:
      if p['perm_name'] == 'owner' and len(p['required_auth']['keys']) > 0:
        owner_key = p['required_auth']['keys'][0]['key']
        continue
      if p['perm_name'] == 'active' and len(p['required_auth']['keys']) > 0:
        active_key = p['required_auth']['keys'][0]['key']
        continue
      #print 'meet neither owner nor active key for account:',account_name
    keys = {
      'owner':  owner_key,
      'active': active_key
    }
    return keys
  else:
    return None


import redis
g_redis = redis.StrictRedis(db = 0)

def has_global_stop_signal():
  return g_redis.get('bac_stopsig') != None

# print progress
processed_count = mp.Value('i', 0)
total_to_process = 0
def step_progress():
  processed_count.value += 1
  progress = 100.0 * processed_count.value / total_to_process
  g_redis.set('bac_progress', progress)
  g_redis.incr('bac_processed')
  print('{:5.1f}% {:6d}/{}'.format(progress, processed_count.value, total_to_process))

def kc_create_accounts_from_mc_snapshot(tag, kc_nodeos_url, account_list):
  result_list = []
  for name in account_list:
    ret = kc_create_account_from_mc_account(kc_nodeos_url, name)
    result_list.append({'_id':name, 'status':ret['status'], 'msg':ret['msg']})
    step_progress()
    if has_global_stop_signal():
      break
  return {'tag':tag, 'result':result_list}

# process callback
results = {}
def job_done(ret):
  results[ret['tag']] = ret['result']

if __name__ == '__main__':
  # print sys.argv
  df = pd.read_csv('accounts.csv',skiprows = 0, usecols=['_id'])
  total_account_count = len(df['_id'])
  total_to_process = total_account_count

  # use redis to record the progress in case lost of terminal
  g_redis.delete(*['bac_stopsig'])
  g_redis.set('bac_total', total_account_count)
  g_redis.set('bac_processed', 0)
  g_redis.set('bac_progress', 0)

  print 'begin processing accounts amount:',total_account_count
  tbegin = time.time()
  seq = 0
  index = 0
  single_job_account_max_count = 10000

  # process pool
  pool = mp.Pool(processes = 5)
  while index < total_account_count:
    if has_global_stop_signal():
      break
    if index + single_job_account_max_count > total_account_count:
      single_job_account_count = total_account_count - index
    else:
      single_job_account_count = single_job_account_max_count

    account_list = df['_id'][index : index + single_job_account_count]
    pool.apply_async(kc_create_accounts_from_mc_snapshot,
                     args = [seq, eosapi.KYLIN_NODEOS_URL, account_list],
                     callback=job_done)
    seq += 1
    index += single_job_account_count

  pool.close()
  pool.join()

  # report time cost
  tdelta = time.time() - tbegin
  timecost = 'time cost: {} min {} sec\n'.format(int(tdelta/60), int(tdelta)%60)
  if not os.path.exists('out'):
    os.makedirs('out')
  fo = open('out/timecost.txt', 'w')
  fo.write(timecost)
  fo.close()

  if len(results) > 0:
    # merge result
    d = []
    for i in range(0, seq):
      d.extend(results[i])

    # save result
    df = pd.DataFrame(data=d, columns=['_id', 'status', 'msg'])
    failed_df = df.loc[df['status'] == 'fail']
    df.to_csv('out/result.csv')
    failed_df.to_csv('out/failed.csv')

    # time cost report
    print timecost, 'time cost saved in "out/timecost.txt"'
    # screen report fail
    if len(failed_df) > 0:
      print '-'*80
      print failed_df
      print '-'*80
      print 'find result in out/result.csv, fail report in out/failed.csv'
    else:
      print 'all done'

  else:
    print 'unexpected error, got no result'

  # delete redis keys
  g_redis.delete(*['bac_stopsig', 'bac_total', 'bac_processed', 'bac_progress'])
