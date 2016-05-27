import os
import yaml
import importlib

basedir = os.path.abspath(os.path.dirname(__file__))

client = os.getenv('CLIENT') or 'grocery'
if client not in ['pay', 'grocery']:
    assert False, u'Client is not provided'
env = os.getenv('HOSTENV') or 'development'
if env not in ['development', 'staging', 'test', 'production']:
    assert False, 'Only development, staging and test environments are supported. Found HOSTENV = '.format(env)

config_file = basedir + '/config/' + client + '/' + env + '.yml'

with open(config_file, 'r') as f:
    CONFIG = yaml.safe_load(f)
APP_NAME = 'grocery_coupon_service'
BASE_DIR = '/var/log'
if env == 'development':
    BASE_DIR = '/tmp'
DATABASE_URL = CONFIG["mysql"]["connection"]
LOG_DIR = BASE_DIR + os.sep + CONFIG["logfile"]["foldername"]
LOG_FILE = LOG_DIR + os.sep + CONFIG["logfile"]["logfilename"]
LOG_FILE_ERROR = BASE_DIR + os.sep + CONFIG["logfile"]["foldername"] + os.sep + CONFIG["logfile"]["errorlogfilename"]
RULESREDISHOST = CONFIG["ruleredis"]["host"]
RULESREDISPORT = CONFIG["ruleredis"]["port"]
RULESREDISDB = CONFIG["ruleredis"]["db"]
SUBSCRIPTIONURL = CONFIG["informationhosturl"] + CONFIG["subscriptionendpoint"]
LOCATIONURL = CONFIG["informationhosturl"] + CONFIG["locationendpoint"]
USERINFOURL = CONFIG["informationhosturl"] + CONFIG["userendpoint"]
USERFROMMOBILEURL = CONFIG["informationhosturl"]+CONFIG["userfromphoneendpoint"]
TOKEN = CONFIG["token"]
MIGRATIONS_DIRECTORY = CONFIG["migrationsdirectory"]

module_name = 'client_method_dict' + '.' + client
module = importlib.import_module(module_name)
method_dict = getattr(module, 'method_dict')
