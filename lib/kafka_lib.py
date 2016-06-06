import simplejson as json
from kafka import KafkaProducer
from kafka.errors import KafkaTimeoutError, NoBrokersAvailable

from config import KAFKAHOST
import logging

logger = logging.getLogger(__name__)

try:
    kafka_producer = KafkaProducer(bootstrap_servers=KAFKAHOST, acks=0)
except NoBrokersAvailable:
    kafka_producer = None


def send_message_to_kafka(topic, key, message):
    """
    :param topic: topic name
    :param key: key to decide partition
    :param message: json serializable object to send
    :return:
    """
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