import json
import boto3

def publish_message(topic, payload):
    iot = boto3.client('iot-data')
    try:
        print ('[publish] topic:' + topic + ', payload:' + json.dumps(payload))
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

def publish_play_sound_effect_request(device_name):
    topic = 'toybox/' + device_name + '/control'
    payload = {
        "type": "play_sound_effect",
        "detail": {
            "sound_effect_type": 'notification',
        }
    }
    publish_message(topic, payload)

def create_ssml_text_for_child(text_to_speech):
    return '<speak><amazon:effect vocal-tract-length="-10%" phonation="soft"><prosody pitch="+30%" rate="85%" volume="x-loud">' + text_to_speech + '</prosody></amazon:effect></speak>'

def lambda_handler(event, context):
    print(event)
    try:
        device_id = event['pathParameters']['deviceId']
        request_body = json.loads(event['body'])
        operation_mode = request_body['operationMode']
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps('request is invalid.')
        }
    
    if operation_mode == 'cleaning':
        publish_play_sound_effect_request(device_id)
        publish_speech_request(device_id, create_ssml_text_for_child('さあ、おもちゃを片付けよう～！。終わったら青いボタンを押してね'))
        update_shadow(device_id, 'mode', 'cleaning')
        update_shadow(device_id, 'is_bgm_playing', True)
    elif operation_mode == 'toy_registration':
        publish_play_sound_effect_request(device_id)
        update_shadow(device_id, 'mode', 'toy_registration')
        publish_speech_request(device_id, '登録するおもちゃを読み込ませてください')
        
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
