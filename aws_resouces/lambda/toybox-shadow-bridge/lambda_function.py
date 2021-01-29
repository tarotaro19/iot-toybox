import json
import boto3

def lambda_handler(event, context):
    print(event)
    iot = boto3.client('iot-data')
    try:
        device_id = event['pathParameters']['deviceId']
        method = event['httpMethod']
        #request_body = json.loads(event['body'])
    except Exception as e:
        return {
            "isBase64Encoded": False,
            'statusCode': 400,
            'headers':{},
            'body': json.dumps('request is invalid.')
        }
    
    if method == 'GET':
        shadow_response = iot.get_thing_shadow(thingName=device_id)
        shadow = json.loads(shadow_response['payload'].read())
        print(shadow)
        return {
        "isBase64Encoded": False,
        'statusCode': 200,
        'headers':{},
        'body': json.dumps(shadow)
        }
        
    return {
        "isBase64Encoded": False,
        'statusCode': 200,
        'headers':{},
        'body': json.dumps('Hello from Lambda!')
    }
