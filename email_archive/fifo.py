import logging


logger = logging.getLogger(__name__)


class FIFOQueue(object):

    def __init__(self, queue_name, connection):
        self.queue_name = queue_name
        self.connection = connection

        self.priorities = (1, 2, 3)
        self.queues = [self.get_queue(p) for p in self.priorities]
        logging.debug('Setup {} with queues {}'.format(self.__class__.__name__, self.queues))

    def get_queue(self, priority):
        return '{}:{}'.format(self.queue_name, priority)

    def push(self, item, priority=2):
        self.queue_length = self.connection.lpush(self.get_queue(priority), item)

    def pop(self, timeout=None):
        if timeout is None:
            for queue in self.queues:
                item = self.connection.rpop(self.queue_name)
                if item is not None:
                    return item
            return None
        else:
            item = self.connection.brpop(self.queues, timeout)
            if item:
                item = item[1]
        return item

    def queue_length(self):
        return sum([self.connection.llen(q) for q in self.queues])

    def __repr__(self):
        return '<{} "{}" length={}>'.format(self.__class__.__name__,
                                            self.queue_name,
                                            self.queue_length())
