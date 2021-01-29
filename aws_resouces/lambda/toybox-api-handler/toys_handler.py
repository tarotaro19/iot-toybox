import json
import boto3
import utils

def create_toy_data(toy_info, request_body):
    if 'name' not in request_body or 'place' not in request_body:
        return None
    data = {}
    data['uid'] = toy_info['uid']
    data['device_id'] = toy_info['device_id']
    data['time'] = toy_info['time']
    data['name'] = request_body['name']
    data['place'] = request_body['place']
    return data

def put_toy(path_paremeters, request_body):
    print('put_toy')
    print(request_body)
    device_id = path_paremeters['deviceId']
    toys = utils.dynamo_scan_toys()
    wait_registraion_key = 'wait_registration'
    print(toys)
    for toy in toys:
        if toy['device_id'] == device_id:
            if wait_registraion_key in toy and toy[wait_registraion_key] == True:
                toy_data = create_toy_data(toy, request_body)
                if toy_data != None:
                    utils.dynamo_put_item(toy_data)
                    speech_text = "おもちゃの名前を、" + request_body['name'] + '。 片付け場所を、' + request_body['place'] + 'で登録しました。'
                    utils.publish_speech_request(device_id, speech_text)
                    return {
                        'statusCode': 200,
                        'body': ''
                    }
                else:
                    return {
                        'statusCode': 400,
                        'body': json.dumps('request body is invalid.')
                    }
    return {
        'statusCode': 400,
        'body': json.dumps('waiting registration toy is not found.')
    }
    
def get_toys(path_paremeters, request_body):
    print('get_toys')
    print(request_body)
    device_id = path_paremeters['deviceId']
    toys = utils.dynamo_scan_toys()
    wait_registraion_key = 'wait_registration'
    print(toys)
    return {
        "isBase64Encoded": False,
        'statusCode': 200,
        'headers':{},
        'body': json.dumps(toys, default=utils.dynamo_json_serialize_default)
    }

def handler(path, path_paremeters, method, request_body):
    if method == 'PUT':
        ret = put_toy(path_paremeters, request_body)
    elif method == 'GET':
        ret = get_toys(path_paremeters, request_body)
    return ret
