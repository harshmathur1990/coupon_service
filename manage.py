import os
from __init__ import create_app
from flask_script import Manager
from flask_script import Server

app = create_app()
manager = Manager(app)
manager.add_command("runserver", Server(host="localhost", port=8000))


@manager.command
def test(coverage=False):
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('test')
    unittest.TextTestRunner(verbosity=2).run(tests)


if __name__ == '__main__':
    manager.run()