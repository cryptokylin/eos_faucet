import tornado.ioloop
import tornado.web
import tornado.httpserver

import json
import requests

import eosapi
import wallet

import os
import re
import ratelimit

# ------------------------------------------------------------------------------------------
# ------ token transfer limiter

def token_limit_exceed(handler):
    write_json_response(handler, {'msg': 'reach 24 hours max token amount'}, 403)

single_get_token_call_amount = 100

ip_24h_token_amount_limiter = ratelimit.RateLimitType(
  name = "ip_24h_token_amount",
  amount = 1000,         # 24 hours amount
  expire = 3600*24,      # 24 hours
  identity = lambda h: h.request.remote_ip,
  on_exceed = token_limit_exceed)


# ------------------------------------------------------------------------------------------
# ------ common functions

def write_json_response(handler, msg, code=200):
  handler.set_status(code)
  handler.set_header('Content-Type', 'application/json; charset=UTF-8')
  handler.write(msg)

def is_valid_account_name(account_name):
  return len(account_name) < 13 and len(account_name) > 0 and not re.search(r'[^a-z1-5\.]', account_name)

def is_valid_newaccount_name(account_name):
  return len(account_name) == 12 and not re.search(r'[^a-z1-5\.]', account_name)

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

def get_first_arg_name_from_request(request):
  args = request.arguments.keys()
  if len(args) == 1:
    return args[0]
  else:
    return ''

def account_exists(account_name):
  payload = json.dumps({'account_name': account_name})
  response = requests.request("POST", eosapi.GET_ACCOUNT, data=payload)
  if response.status_code == 200:
    ret = json.loads(response.text)
    return ret['account_name'] == account_name
  else:
    return False

def generate_key():
  ret = os.popen('cleos create key').read()
  array = ret.split()
  if len(array) == 6:
    return { 'private': array[2], 'public': array[5] }
  else:
    return None

def unlock_wallet_if_locked():
  unlocked = False
  if is_wallet_locked():
    print('wallet "{}" locked, try to unlock...'.format(wallet.NAME))
    if unlock_wallet():
      unlocked = True
      print('wallet "{}" unlocked!'.format(wallet.NAME))
    else:
      print('wallet "{}" unlock failed'.format(wallet.NAME))
  else:
    unlocked = True
  return unlocked


# ------------------------------------------------------------------------------------------
# ------ Get Token Handler

class GetTokenHandler(tornado.web.RequestHandler):

  def __init__(self, application, request, **kwargs):
    tornado.web.RequestHandler.__init__(self, application, request, **kwargs)

  def _assembly_args(self, data):
    if data.has_key('account') and is_valid_account_name(data['account']):
      p = {}
      p['from']     = wallet.ACCOUNT
      p['to']       = data['account']
      p['quantity'] = single_get_token_call_amount
      p['symbol']   = "EOS"
      if data.has_key('memo'): p['memo']   = data['memo']
      else:                    p['memo']   = ''
      return p
    else:
      return None

  def _os_cmd_transfer(self, param):
    cmdline = 'cleos --url {} transfer {} {} "{} {}" {}'.format(eosapi.NODEOS_URL,
                                                                param['from'],
                                                                param['to'],
                                                                param['quantity'],
                                                                param['symbol'],
                                                                param['memo'])
    result = os.system(cmdline)
    return result == 0

  def _make_transfer(self, p):
    if unlock_wallet_if_locked():
      return self._os_cmd_transfer(p)
    else:
      return False

  def _handle(self, data):
    param = self._assembly_args(data)
    if param:
      if self._make_transfer(param):
        ip_24h_token_amount_limiter.increase_amount(param['quantity'], self)
        write_json_response(self, {'msg': 'succeeded'})
      else:
        failmsg = {'msg': 'transaction failed, possible reason: account does not exist'}
        write_json_response(self, failmsg, 400)
    else:
      fmtmsg = {'msg':'please use request with URL of format: http://13.125.53.113/get_token?valid_account_name'}
      write_json_response(self, fmtmsg, 400)

  @ratelimit.limit_by(ip_24h_token_amount_limiter)
  def post(self):
    data = {'account': get_first_arg_name_from_request(self.request)}
    # data = json.loads(self.request.body.decode())
    self._handle(data)

  @ratelimit.limit_by(ip_24h_token_amount_limiter)
  def get(self):
    data = {'account': get_first_arg_name_from_request(self.request)}
    self._handle(data)


# ------------------------------------------------------------------------------------------
# ------ account creation limiter

def newaccount_limit_exceed(handler):
    write_json_response(handler, {'msg': 'reach 24 hours max amount of account creation'}, 403)

ip_24h_newaccount_amount_limiter = ratelimit.RateLimitType(
  name = "ip_24h_newaccount_amount",
  amount = 1000,         # 24 hours amount
  expire = 3600*24,      # 24 hours
  identity = lambda h: h.request.remote_ip,
  on_exceed = newaccount_limit_exceed)


# ------------------------------------------------------------------------------------------
# ------ Create Account Handler

class CreateAccountHandler(tornado.web.RequestHandler):

  def __init__(self, application, request, **kwargs):
    tornado.web.RequestHandler.__init__(self, application, request, **kwargs)

  def _assembly_args(self, account_name, owner_key, active_key):
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

  def _os_cmd_create_account(self, p):
    cmdline = 'cleos --url {} system newaccount --stake-net \'{}\' --stake-cpu \'{}\' --buy-ram-kbytes {} {} {} {} {}'.format(
      eosapi.NODEOS_URL,
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

  def _create_account(self, p):
    if unlock_wallet_if_locked():
      return self._os_cmd_create_account(p)
    else:
      return False

  def _handle(self, request):
    name = get_first_arg_name_from_request(request)

    if not is_valid_newaccount_name(name):
      failmsg = {'msg': 'failed, unsupported account name \'{}\''.format(name)}
      write_json_response(self, failmsg, 400)
      return

    if account_exists(name):
      failmsg = {'msg': 'failed, account \'{}\' exists already'.format(name)}
      write_json_response(self, failmsg, 400)
      return

    owner_key = generate_key()
    active_key = generate_key()
    if owner_key and active_key:
      p = self._assembly_args(name, owner_key['public'], active_key['public'])
      if self._create_account(p):
        ip_24h_newaccount_amount_limiter.increase_amount(1, self)
        retmsg = {
          'msg':      'succeeded',
          'account':  name,
          'keys':     { 'owner_key':  owner_key, 'active_key': active_key }
        }
        write_json_response(self, retmsg)
      else:
        failmsg = {'msg': 'failed, failed to createa account'}
        write_json_response(self, failmsg, 400)
    else:
      failmsg = {'msg': 'failed, failed to generate keys'}
      write_json_response(self, failmsg, 400)

  @ratelimit.limit_by(ip_24h_newaccount_amount_limiter)
  def post(self):
    self._handle(self.request)

  @ratelimit.limit_by(ip_24h_newaccount_amount_limiter)
  def get(self):
    self._handle(self.request)


# ------------------------------------------------------------------------------------------
# ------ service app

def make_app():
  return tornado.web.Application([
    (r"/get_token", GetTokenHandler),
    (r"/create_account", CreateAccountHandler),
  ])

if __name__ == "__main__":
  app = make_app()
  server = tornado.httpserver.HTTPServer(app)
  server.bind(80)
  server.start(0)
  tornado.ioloop.IOLoop.current().start()
