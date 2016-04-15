class User(object):
    def __init__(self, **kwargs):
        self.agent_id = kwargs.get('agent_id')
        self.agent_name = kwargs.get('agent_name')
