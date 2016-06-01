import os
import newrelic.agent
from __init__ import create_app
from flask_script import Manager
from flask_script import Server
import config
from flask_migrate import Migrate, MigrateCommand
from src.sqlalchemydb import CouponsAlchemyDB
from kafka_apps.pay.consumer import kafka_consumer
from flask_script import Command

if config.env and config.env in ['production', 'staging']:
    newrelic_cfg_file = os.path.join(os.getcwd(), "conf", u'newrelic-{}-{}.ini'.format(config.env, config.client))
    newrelic.agent.initialize(newrelic_cfg_file)

app = create_app()
app.config['SQLALCHEMY_DATABASE_URI'] = config.DATABASE_URL
db = CouponsAlchemyDB()
migrate = Migrate(app, db, directory=config.MIGRATIONS_DIRECTORY)
manager = Manager(app)
manager.add_command("runserver", Server(host="localhost", port=config.CONFIG["port"]))
manager.add_command("db", MigrateCommand)
manager.add_command("kafka_consumer", Command(kafka_consumer))


@manager.command
def test(coverage=False):
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('test_'+config.client)
    unittest.TextTestRunner(verbosity=2).run(tests)


if __name__ == '__main__':
    manager.run()
