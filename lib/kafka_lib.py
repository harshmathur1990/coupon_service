import simplejson as json
from kafka import KafkaProducer
from kafka.client import KafkaClient
from config import KAFKAHOST


kafka_producer = KafkaProducer(bootstrap_servers=KAFKAHOST)


def send_message_to_kafka(topic, key, message):
    """
    :param topic: topic name
    :param key: key to decide partition
    :param message: json serializable object to send
    :return:
    """
    data = json.dumps(message)
    kafka_producer.send(topic, key=str(key), value=data)
