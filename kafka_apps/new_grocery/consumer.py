import logging
import simplejson as json
from kafka import KafkaConsumer
from config import KAFKAHOST, HOST
from lib.utils import make_api_call
from src.sqlalchemydb import CouponsAlchemyDB
from config import TEST_USER, TEST_TOKEN, TEST_TOPIC_KAFKA
from flask_script import Manager

logger = logging.getLogger(__name__)


KafkaTestingConsumerCommand = Manager(usage="Consumer for testing the prod requests by replaying on staging")


@KafkaTestingConsumerCommand.option('-g', '--group_ids', dest='group_no', default=1,
                       help=("group no (musr be different for different partitions)"))
def replay_test(group_no):
    group_id = TEST_TOPIC_KAFKA + u'{}'.format(group_no)
    consumer = KafkaConsumer(bootstrap_servers=KAFKAHOST, group_id=group_id, enable_auto_commit=True)
    consumer.subscribe([TEST_TOPIC_KAFKA])
    consumer.topics()
    consumer.poll(0)
    while True:
        for message in consumer:
            data = json.loads(message.value)
            end_point = data['url']
            body = data['body']
            response = data['response']
            params = data['query']
            url = HOST + end_point
            headers = {
                'X-API-USER': TEST_USER,
                'X-API-TOKEN': TEST_TOKEN
            }
            response_on_staging_obj = make_api_call(
                url=url, body=json.loads(body), method='POST', headers=headers, params=params)
            response_on_staging = response_on_staging_obj.text

            data = {
                'url': end_point,
                'body': body,
                'prod_response': response,
                'params': params,
                'staging_response': response_on_staging,
                'match': response_on_staging == response
            }

            db = CouponsAlchemyDB()
            db.begin()
            try:
                db.insert_row("auto_tester", **data)
                db.commit()
            except Exception as e:
                logger.exception(e)
                db.rollback()
