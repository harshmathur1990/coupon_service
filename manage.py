import os
import newrelic.agent
from __init__ import create_app
from flask_script import Manager
from flask_script import Server
import config


if config.env == "production":
    newrelic_cfg_file = os.path.join(os.getcwd(), "conf", "newrelic-%s.ini" % config.env)
    newrelic.agent.initialize(newrelic_cfg_file)

app = create_app()
manager = Manager(app)
manager.add_command("runserver", Server(host="localhost", port=config.CONFIG["port"]))


@manager.command
def test(coverage=False):
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('test')
    unittest.TextTestRunner(verbosity=2).run(tests)


if __name__ == '__main__':
    manager.run()