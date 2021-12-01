#!/usr/bin/env python
#
# Copyright chenyuqin@vivo
#
# latest update: 07/20/2016

"""

 Signing data on a remote server.
 
 Usage:
 
        simple_sign.py -s <server> -k <key> [-b base] [-a algorithm] <input_data> <output_sig>

"""

import os
import sys
import hashlib
import tempfile
import subprocess
import getpass
import socket
import time
import getopt
import stat

_CMS_NAME = 'cms'

class Options(object): pass
OPTIONS = Options()
OPTIONS.server          = 'compiler213'
OPTIONS.sign_base       = '/opt1/cmsder/workspace/simple_sign'          # as so far, tools are put in here on server
OPTIONS.key             = ''
OPTIONS.algorithm       = 'sha256'
OPTIONS.unique_name     = ''
OPTIONS.unique_space    = ''
OPTIONS.tempfiles       = []

def Usage():

  print __doc__
  print """ Options:\n
  -s [--server] specify sign server\n
  -b [--base] specify sign tool location on sign server (use it only if you know the location!)\n
  -k [--key] specify key to use\n
  -a [--algorithm] specify hash algorithm (sha1, sha256), default sha256\n\n\n"""

def Option_Handler(argv):

  try:
    opts, args = getopt.getopt(argv, 's:b:k:a:', ['server=', 'base=', 'key=', 'algorithm='])
  except getopt.GetoptError:
    Usage()
    sys.exit(1)
  for opt, arg in opts:
    if opt in ('-s', '--server'):
      OPTIONS.server = arg
    elif opt in ('-b', '--base'):   # for we won't check whether if the sign_base is appropriate or not so far, so you needs to use '-b' with cautions (so it might be used rarely)
      OPTIONS.sign_base = arg
    elif opt in ('-k', '--key'):
      OPTIONS.key = arg
    elif opt in ('-a', '--algorithm'):
      if arg in ('sha1', 'sha256'):
        OPTIONS.algorithm = arg

  if OPTIONS.server == '':
    Usage()
    print '*** you should specify the signer server (ex. compilerXXX) ***'
    sys.exit(1)
  if OPTIONS.sign_base == '':
    Usage()
    print '*** you should specify sign base on signer server (only if you know the location) ***'
    sys.exit(1)
  if OPTIONS.key == '':
    Usage()
    print '*** you should specify key ***'
    sys.exit(1)

  return args

def system_command(command_list, stderr_to_temp=False, shell=False, silent=False):
  tmp_stderr_file = None

  if silent == True:
    tmp_stderr_file = open('/dev/null', 'w')
  elif stderr_to_temp == True:
    tmp_stderr_file = tempfile.NamedTemporaryFile(delete=True)
  try:
    return subprocess.check_output(command_list, stderr=tmp_stderr_file, shell=shell)
  except subprocess.CalledProcessError:
    print ("please wait 15s, will run it again...")
    time.sleep(15)
    return subprocess.check_output(command_list, stderr=tmp_stderr_file, shell=shell)

def store_data_to_temp_file(data):
  temp_file = tempfile.NamedTemporaryFile(delete=False)
  temp_file.write(data)
  temp_file.close()
  OPTIONS.tempfiles.append(temp_file.name)
  return temp_file.name

def SimpleSign(args):

  if (len(args) != 2):
    Usage()
    sys.exit(1)
  input_data, output_sig = args[0:]

  print ('start signing "%s" ...' % (input_data,))

  f = open(input_data, 'rb')
  data = f.read()
  f.close()

  if os.path.isdir(output_sig):
    print ('*** %s is a directory ***' % (output_sig,))
    sys.exit(1)

  if OPTIONS.algorithm == 'sha256':
    OID = '\x30\x31\x30\x0D\x06\x09\x60\x86\x48\x01\x65\x03\x04\x02\x01\x05\x00\x04\x20'
    hash_data = OID + hashlib.sha256(data).digest()
  elif OPTIONS.algorithm == 'sha1':
    OID = '\x30\x21\x30\x09\x06\x05\x2B\x0E\x03\x02\x1A\x05\x00\x04\x14'
    hash_data = OID + hashlib.sha1(data).digest()
  else:
    Usage()
    sys.exit(1)

  hash = store_data_to_temp_file(hash_data)
  os.chmod(hash, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

  command_list = [_CMS_NAME, '-i', OPTIONS.server, 'push', hash, os.path.join(OPTIONS.unique_space, os.path.basename(input_data) + '.hash'), '--direct']
  system_command(command_list, silent = True)

  command_list = [_CMS_NAME, '-i', OPTIONS.server, 'shell',
                  os.path.join(OPTIONS.sign_base, 'user_masker'),
                  'python',
                  os.path.join(OPTIONS.sign_base, 'simple_sign.py'),
                  OPTIONS.key,
                  os.path.join(OPTIONS.unique_space, os.path.basename(input_data) + '.hash'),
                  os.path.join(OPTIONS.unique_space, os.path.basename(input_data) + '.sig')]
  print (system_command(command_list))

  command_list = [_CMS_NAME, '-i', OPTIONS.server, 'pull', os.path.join(OPTIONS.unique_space, os.path.basename(input_data) + '.sig'), output_sig, '--direct']
  system_command(command_list, silent = True)
  os.chmod(output_sig, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

  print ('created "%s"' % (output_sig,))
  print ('done.')

def Cleanup():
  for temp_file in OPTIONS.tempfiles:
    os.remove(temp_file)
  if OPTIONS.server != '' and OPTIONS.unique_name != '':
    command_list = [_CMS_NAME, '-i', OPTIONS.server, 'shell', 'rm -rf ' + OPTIONS.unique_space]
    system_command(command_list, silent = True)

def main(argv):

  args = Option_Handler(argv)

  temp_file = tempfile.NamedTemporaryFile(suffix = '_simple_sign')
  OPTIONS.unique_name = getpass.getuser() + '_' + socket.gethostname() + '_' + time.strftime('%Y-%m-%d_%H:%M:%S', time.localtime(time.time())) + '_' + os.path.basename(temp_file.name)
  temp_file.close()
  OPTIONS.unique_space = OPTIONS.sign_base + '/todo/' + OPTIONS.unique_name

  SimpleSign(args)

  # finally, to save signing record (notice that md5sum.sh would filter some files)
  command_list = [_CMS_NAME, '-i', OPTIONS.server, 'shell',
                  'md5sum.sh', '-d',
                  OPTIONS.unique_space]
  system_command(command_list, silent=True)
  command_list = [_CMS_NAME, '-i', OPTIONS.server, 'shell',
                  'mv',
                  OPTIONS.unique_space + '/md5.txt',
                  OPTIONS.sign_base + '/record/' + OPTIONS.unique_name + '.txt']
  system_command(command_list, silent=True)

if __name__ == '__main__':

  try:
    main(sys.argv[1:])
  finally:
    # clean on sign server (TODO: clean when fail to communicate with server)
    Cleanup()
