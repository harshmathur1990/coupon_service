import logging
import sqlalchemy
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
                       help=("group no (must be different for different partitions)"))
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
            if end_point.endswith(('check', 'apply')):
                body_data = json.loads(body)
                for product in body_data.get('products', list()):
                    product['subscription_id'] = product.get('item_id')
                body = json.dumps(body_data)
            params = data['query']
            response = data['response']
            url = HOST + end_point
            headers = {
                'X-API-USER': TEST_USER,
                'X-API-TOKEN': TEST_TOKEN,
                'Content-Type': 'Application/Json'
            }

            response_on_staging_obj = make_api_call(
                url=url, body=json.loads(body), method='POST', headers=headers, params=params)
            response_on_staging = response_on_staging_obj.text

            data = {
                'url': end_point,
                'body': body,
                'params': json.dumps(params),
                'prod_response': response,
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


def get_url_from_end_point(end_point):
    if end_point.endswith('check'):
        return HOST + u'/vouchers/grocery/v1/check'
    if end_point.endswith('apply'):
        return HOST + u'/vouchers/grocery/v1/apply'
    else:
        return HOST + u'{}'.format(end_point)