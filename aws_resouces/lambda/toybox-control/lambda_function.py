import json
import boto3

def publish_message(topic, payload):
    iot = boto3.client('iot-data')
    try:
        print ('[publish] tpoic:' + topic + ', payload:' + json.dumps(payload))
        iot.publish(topic=topic, qos=0, payload=json.dumps(payload, ensure_ascii=False))
    except Exception as e:
        print(e)

def lambda_handler(event, context):
    print(event)
    iot = boto3.client('iot-data')
    try:
        device_id = event['pathParameters']['deviceId']
        topic = 'toybox/' + device_id + '/control'
        request_body = json.loads(event['body'])
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps('request is invalid.')
        }
    publish_message(topic, request_body)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
