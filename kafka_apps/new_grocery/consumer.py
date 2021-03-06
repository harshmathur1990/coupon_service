import logging
from sqlalchemy.exc import DataError
import simplejson as json
from config import KAFKAHOST, HOST
from lib.utils import make_api_call
from src.sqlalchemydb import CouponsAlchemyDB
from config import TEST_USER, TEST_TOKEN, TEST_TOPIC_KAFKA, ZOOKEEPER
from flask_script import Manager
from pykafka import KafkaClient, common

logger = logging.getLogger(__name__)

KafkaTestingConsumerCommand = Manager(usage="Consumer for testing the prod requests by replaying on staging")


@KafkaTestingConsumerCommand.option('-g', '--group_ids', dest='group_no', default=1,
                       help=("group no (must be different for different partitions)"))
def replay_test(group_no):
    try:
        client = KafkaClient(hosts=KAFKAHOST)
    except Exception as e:
        return
    group_id = TEST_TOPIC_KAFKA + u'{}'.format(group_no)
    try:
        topic = client.topics[TEST_TOPIC_KAFKA]
        balanced_consumer = topic.get_balanced_consumer(
            consumer_group=str(group_id),
            auto_commit_enable=True,
            reset_offset_on_start=True,
            auto_offset_reset=common.OffsetType.LATEST,
            use_rdkafka=False,
            zookeeper_connect=ZOOKEEPER
        )
        for message in balanced_consumer:
            if message is not None:
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
                    'body_varchar': body,
                    'prod_response_varchar': response,
                    'staging_response_varchar': response_on_staging,
                    'match': response_on_staging == response
                }

                db = CouponsAlchemyDB()
                db.begin()
                try:
                    try:
                        db.insert_row("auto_tester", **data)
                    except DataError:
                        del data['body_varchar']
                        del data['prod_response_varchar']
                        del data['staging_response_varchar']
                        db.insert_row("auto_tester", **data)
                    db.commit()
                except Exception as e:
                    logger.exception(e)
                    db.rollback()
    except Exception as e:
        logger.exception(e)
