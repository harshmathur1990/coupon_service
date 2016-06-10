import os
import yaml
import importlib

basedir = os.path.abspath(os.path.dirname(__file__))

client = os.getenv('CLIENT')
if client not in ['pay', 'grocery', 'new_grocery']:
    assert False, u'Client is not provided'
env = os.getenv('HOSTENV') or 'development'
if env not in ['development', 'staging', 'test', 'production']:
    assert False, 'Only development, staging and test environments are supported. Found HOSTENV = '.format(env)

config_file = basedir + '/config/' + client + '/' + env + '.yml'

with open(config_file, 'r') as f:
    CONFIG = yaml.safe_load(f)
APP_NAME = client+'_coupon_service'
BASE_DIR = '/var/log/couponlogs'
if env == 'development':
    BASE_DIR = '/tmp'
DATABASE_URL = CONFIG["mysql"]["connection"]
LOG_DIR = BASE_DIR + os.sep + client
LOG_FILE = LOG_DIR + os.sep + CONFIG["logfile"]["logfilename"]
LOG_FILE_ERROR = LOG_DIR + os.sep + CONFIG["logfile"]["errorlogfilename"]
RULESREDISHOST = CONFIG["ruleredis"]["host"]
RULESREDISPORT = CONFIG["ruleredis"]["port"]
RULESREDISDB = CONFIG["ruleredis"]["db"]
MIGRATIONS_DIRECTORY = CONFIG["migrationsdirectory"]
KAFKAHOST = CONFIG["kafka"]["host"]
ZOOKEEPER = CONFIG["kafka"]["zookeeper"]
TEST_USER = CONFIG["testtoken"]["user"]
TEST_TOKEN = CONFIG["testtoken"]["token"]
TEST_TOPIC_KAFKA = CONFIG["testtoken"]["kafkatopic"]
HOST = CONFIG["testtoken"]["hosttohit"]
PUSHTOKAFKA = CONFIG["testtoken"]["pushtokafka"]

if client == 'grocery':
    SUBSCRIPTIONURL = CONFIG["informationhosturl"] + CONFIG["subscriptionendpoint"]
    LOCATIONURL = CONFIG["informationhosturl"] + CONFIG["locationendpoint"]
    USERINFOURL = CONFIG["informationhosturl"] + CONFIG["userendpoint"]
    USERFROMMOBILEURL = CONFIG["informationhosturl"]+CONFIG["userfromphoneendpoint"]
    TOKEN = CONFIG["token"]

if client == 'new_grocery':
    SUBSCRIPTIONURL = CONFIG["subscriptionendpoint"]
    SUBSCRIPTIONHEADERS = CONFIG["subscriptionheaders"]
    LOCATIONURL = CONFIG["locationendpoint"]
    USERINFOURL = CONFIG["userendpoint"]


module_name = 'client_method_dict' + '.' + client
module = importlib.import_module(module_name)
method_dict = getattr(module, 'method_dict')
