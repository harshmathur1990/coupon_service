import os
import yaml

basedir = os.path.abspath(os.path.dirname(__file__))

env = os.getenv('SETTINGS') or 'development'

config_file = basedir + '/config/' + env + '.yml'

with open(config_file, 'r') as f:
    CONFIG = yaml.safe_load(f)

DATABASE_URL = CONFIG["mysql"]["connection"]
LOG_FILE = CONFIG["logfile"]["foldername"] + os.sep + CONFIG["logfile"]["logfilename"]
LOG_FILE_ERROR = CONFIG["logfile"]["foldername"] + os.sep + CONFIG["logfile"]["errorlogfilename"]
RULESREDISHOST = CONFIG["ruleredis"]["host"]
RULESREDISPORT = CONFIG["ruleredis"]["port"]
RULESREDISDB = CONFIG["ruleredis"]["db"]


