import simplejson as json
from kafka import KafkaConsumer
from config import KAFKAHOST


def kafka_consumer():
    consumer = KafkaConsumer(bootstrap_servers=KAFKAHOST, group_id="test_price_3", enable_auto_commit=True)
    consumer.subscribe(['harshtest1'])
    consumer.topics()
    consumer.poll(0)
    while True:
        for message in consumer:
            data = json.loads(message.value)
            print data
