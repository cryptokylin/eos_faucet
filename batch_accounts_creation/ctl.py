
import sys
import redis

g_redis = redis.StrictRedis(db = 0)

if __name__ == '__main__':

  if len(sys.argv) == 2 and (sys.argv[1] == 'progress' or sys.argv[1] == 'stop'):
    total = g_redis.get('bac_total')
    processed = g_redis.get('bac_processed')
    progress_percent = g_redis.get('bac_progress')

    if total != None:
      if sys.argv[1] == 'progress':
        total = int(total)
        processed = int(processed)
        progress_percent = float(progress_percent)
        print('BAC: {:5.1f}% {:6d}/{}'.format(progress_percent, processed, total))
      elif sys.argv[1] == 'stop':
        g_redis.set('bac_stopsig', 1)
      else:
        pass
    else:
      print 'BAC not found, not started or finished already'
  else:
    print 'using: python',sys.argv[0],'progress|stop'
 
