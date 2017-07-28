import redis


class FIFOQueue(object):

    queue_length = None

    def __init__(self, queue_name, connection):
        self.queue_name = queue_name
        self.connection = connection
        self.queue_length = connection.llen(self.queue_name)

    def push(self, item):
        self.queue_length = self.connection.lpush(self.queue_name, item)

    def pop(self, timeout=None):
        if timeout is None:
            item = self.connection.rpop(self.queue_name)
        else:
            item = self.connection.brpop(self.queue_name, timeout)
            if item:
                item = item[1]
        self.queue_length = self.connection.llen(self.queue_name)
        return item

    def __repr__(self):
        return '<{} length={}>'.format(self.__class__.__name__,
                                       self.queue_length is not None and self.queue_length or 'unknown')
