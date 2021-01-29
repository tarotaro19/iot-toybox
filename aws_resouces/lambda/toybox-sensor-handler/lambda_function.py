import json
import boto3
import utils

def extract_device_name_from_client_id(client_id):
    device_name = client_id.replace('toybox/', '')
    return device_name

def check_cleaning_finish(current_weight, total_toy_weight):
    if current_weight > total_toy_weight*0.9:
        return True
    else:
        return False
        
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
    
def publish_play_sound_effect_request(device_name, sound_type):
    topic = 'toybox/' + device_name + '/control'
    payload = {
        "type": "play_sound_effect",
        "detail": {
            "sound_effect_type": sound_type,
        }
    }
    publish_message(topic, payload)
    

def button_handler(event):
    print('button hanlder')
    iot = boto3.client('iot-data')
    value = event['value']
    client_id = event['client_id']
    if value == 'blue':
        # get current mode with shadow
        device_name = extract_device_name_from_client_id(client_id)
        shadow_response = iot.get_thing_shadow(thingName=device_name)
        shadow = json.loads(shadow_response['payload'].read())
        mode = shadow['state']['reported']['mode']
        current_weight = shadow['state']['reported']['weight']
        total_toy_weight = shadow['state']['reported']['total_toy_weight']
        
        # check finish or not
        if mode == 'cleaning':
            finish = check_cleaning_finish(current_weight, total_toy_weight)
            if finish:
                # change mode to standby
                update_shadow(device_name, 'mode', 'standby')
                # stop bgm
                update_shadow(device_name, 'is_bgm_playing', False)
                # sound effect
                publish_play_sound_effect_request(device_name, 'good')
                # speech complete message
                publish_speech_request(device_name, utils.create_ssml_text_for_child('片付けできたね！。すごい！'))
                publish_play_sound_effect_request(device_name, 'cheer')
            else:
                publish_play_sound_effect_request(device_name, 'nogood')
                publish_speech_request(device_name, utils.create_ssml_text_for_child('まだおもちゃが片付いてないよ！'))
 

def dynamodb_put_item(item):
    dynamodb = boto3.resource('dynamodb')
    dynamo_table = dynamodb.Table('dynamodb-grouph-toybox-toys-test')
    dynamo_table.put_item(Item=item)
 
def rfid_handler(event):
    print('RFID hanlder')
    iot = boto3.client('iot-data')
    client_id = event['client_id']
    device_name = extract_device_name_from_client_id(client_id)
    event_time = event['time']
    event_uid = event['uid']
    event_text = event['text']
    wait_registration = False
    if 'wait_registration' in event:
        wait_registration = True
        
    # toy properties registration mode
    if wait_registration:
        # put to Dynamodb as registration toy
        item = {
            "uid" : event_uid,
            "device_id" : device_name,
            "time" : event_time,
            "wait_registration" : True
        }
        dynamodb_put_item(item)
        # reset toybox mode to "standby"
        update_shadow(device_name, 'mode', 'standby')
        publish_speech_request(device_name, 'おもちゃの情報を入力して下さい')
        return
    
    # cleaning mode
    shadow_response = iot.get_thing_shadow(thingName=device_name)
    shadow = json.loads(shadow_response['payload'].read())
    mode = shadow['state']['reported']['mode']
    current_weight = shadow['state']['reported']['weight']
    total_toy_weight = shadow['state']['reported']['total_toy_weight']
    if mode == 'cleaning':
        toy_properties = utils.dynamo_scan_with_uid(event_uid)
        message = '「' + toy_properties['name'] + '」は、「' + toy_properties['place'] + '」に片付けてね！'
        print(message)
        publish_speech_request(device_name, utils.create_ssml_text_for_child(message))
    

def lambda_handler(event, context):
    print(event)
    try:
        client_id = event['client_id']
        sensor_type = event['sensor_type']
    except Exception as e:
        print(e)
        return {
            'statusCode': 400,
            'body': json.dumps('event data is invalid.')
        }
        
    if sensor_type == 'weight':
        print('weight sensor data recieved')
        value = event['value']
        diff = event['diff']
    elif sensor_type == 'button':
        button_handler(event)
    elif sensor_type == 'rfid':
        rfid_handler(event)
    else:
        print('not supported')
    
    
    '''
    if diff < 0:
        text_to_speech = message_toy_out
    else:
        text_to_speech = message_toy_in
    payload = {
        "type": "speech",
        "detail": {
            "text": text_to_speech,
        }
    }
    
    try:
        iot.publish(
            topic=topic,
            qos=0,
            payload=json.dumps(payload, ensure_ascii=False)
        )
    except Exception as e:
        print(e)
        return {
            'statusCode': 400,
            'body': json.dumps('failed to publish message.')
        }
    '''
    
    return {
        'statusCode': 200
    }
