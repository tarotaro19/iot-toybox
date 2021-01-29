import json
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from boto3.dynamodb.types import Binary

### DynamoDB
dynamodb_toys_table_name = 'dynamodb-grouph-toybox-toys-test'
def dynamo_scan_toys():
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(dynamodb_toys_table_name)
    toys = table.scan()
    return toys['Items']
    
def dynamo_put_item(item):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(dynamodb_toys_table_name)
    table.put_item(Item=item)

def dynamo_json_serialize_default(obj) -> object:
    if isinstance(obj, Decimal):
        if int(obj) == obj:
            return int(obj)
        else:
            return float(obj)
    elif isinstance(obj, Binary):
        return obj.value
    elif isinstance(obj, bytes):
        return obj.decode()
    elif isinstance(obj, set):
        return list(obj)
    try:
        return str(obj)
    except Exception:
        return None

### IoT Core
def publish_message(topic, payload):
    iot = boto3.client('iot-data')
    try:
        print ('[publish] tpoic:' + topic + ', payload:' + json.dumps(payload))
        iot.publish(topic=topic, qos=0, payload=json.dumps(payload, ensure_ascii=False))
    except Exception as e:
        print(e)
        
def update_shadow(device_name, key, value):
    topic = '$aws/things/' + device_name + '/shadow/update'
    message = {}
    desired = {}
    desired[key] = value
    message = {"state": {"desired": desired}}
    publish_message(topic, message)
    
def publish_speech_request(device_name, text):
    topic = 'toybox/' + device_name + '/control'
    payload = {
        "type": "speech",
        "detail": {
            "text": text,
        }
    }
    publish_message(topic, payload)
