import simplejson as json
from kafka import KafkaProducer
from kafka.errors import KafkaTimeoutError, NoBrokersAvailable
from utils import can_push_to_kafka

from config import KAFKAHOST
import logging

logger = logging.getLogger(__name__)


class CouponsKafkaProducer(object):

    instance = None

    def __init__(self):
        pass

    @staticmethod
    def create_kafka_producer():
        kafka_instance_required = can_push_to_kafka()
        if kafka_instance_required:
            if not CouponsKafkaProducer.instance:
                try:
                    CouponsKafkaProducer.instance = KafkaProducer(bootstrap_servers=KAFKAHOST, acks=0)
                except NoBrokersAvailable as e:
                    CouponsKafkaProducer.instance = None
                    logger.info(e)
                except Exception as e:
                    CouponsKafkaProducer.instance = None
                    logger.exception(e)
        else:
            CouponsKafkaProducer.instance = None

    @staticmethod
    def get_kafka_producer():
        if not can_push_to_kafka():
            CouponsKafkaProducer.destroy_instance()
        return CouponsKafkaProducer.instance

    @staticmethod
    def destroy_instance():
        CouponsKafkaProducer.instance = None

if can_push_to_kafka():
    CouponsKafkaProducer.create_kafka_producer()


def send_message_to_kafka(topic, key, message):
    """
    :param topic: topic name
    :param key: key to decide partition
    :param message: json serializable object to send
    :return:
    """
    kafka_producer = CouponsKafkaProducer.get_kafka_producer()
    if not kafka_producer:
        return
    data = json.dumps(message)
    try:
        kafka_producer.send(topic, key=str(key), value=data)
    except KafkaTimeoutError as e:
        logger.info(e)
        pass
    except Exception as e:
        logger.exception(e)
        pass
