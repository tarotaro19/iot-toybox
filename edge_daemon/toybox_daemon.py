from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import logging
import time
import argparse
import json
import threading
from boto3 import client
from playsound import playsound
import settings as settings
from weight_sensor import WeightSensor
from iot_core_client import IoTCoreClient

### Logger
logger = logging.getLogger("ToyboxDaemon")
logger.setLevel(logging.DEBUG)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s\t%(levelname)s\t%(name)s\t%(funcName)s\t%(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

def downloadAndSpeechText(textToSpeech):
    polly = client("polly", region_name=settings.REGION_NAME, aws_access_key_id=settings.AWS_ACCESS_KEY_ID, aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
    response = polly.synthesize_speech(
                Text = textToSpeech,
                OutputFormat = "mp3",
                VoiceId = "Mizuki")

    file = open("test.mp3", "wb")
    file.write(response["AudioStream"].read())
    file.close()
    playsound("test.mp3")

    
def subscription_callback(client, userdata, message):
    logger.info("Received a new message: ")
    logger.info('from topic: ' + message.topic)
    logger.info('message: ' + str(message.payload))

    request = json.loads(message.payload)
    requestType = request['type']
    requestDetail = request['detail']
    logger.info ('requestType: ' + requestType)
    logger.info ('requestDetail: ' + str(requestDetail))
    downloadAndSpeechText(requestDetail['text'])

def create_publish_message_weight_sensor (value):
    message = {}
    message['time'] = int(time.time())
    message['value'] = int(value)
    return json.dumps(message)
    
def weight_sensor_worker(weight_sensor, iot_core, device_id):
    interval = 1
    last_publish_value = -1000
    publish_topic = 'toybox/' + device_id + '/sensor/weight'
    while True:
        sensor_val = int(weight_sensor.get_value())
        if abs(last_publish_value - sensor_val) > 10:
            message = create_publish_message_weight_sensor (sensor_val)
            iot_core.publish(publish_topic, message)
            last_publish_value = sensor_val
            logger.info('weight sensor val : ' + str(sensor_val))
        time.sleep(1)


def main():    
    # IoT core
    logger.info('initialize IoT Core')
    iot_core = IoTCoreClient()
    iot_core_client_id = 'toybox/' + settings.DEVICE_ID
    subscribe_topic = 'toybox/' + settings.DEVICE_ID + '/control'
    iot_core.init(settings.IOT_CORE_HOST, settings.IOT_CORE_PORT, settings.IOT_CORE_ROOT_CA_PATH, settings.IOT_CORE_PRIVATE_KEY_PATH, settings.IOT_CORE_CERTIFICATE_PATH, iot_core_client_id)
    iot_core.subscribe(subscribe_topic, subscription_callback)
    
    # Weight sensor
    logger.info('initialize weight sensor')
    weight_sensor = WeightSensor()
    weight_sensor.init_sensor(settings.WEIGHT_SENSOR_OUTPUT_PER_GRAM, settings.WEIGHT_SENSOR_OFFSET)
    weight_sensor_thread = threading.Thread(target=weight_sensor_worker, args=(weight_sensor, iot_core, settings.DEVICE_ID))
    weight_sensor_thread.start()    
    
    time.sleep(2)
    
    while True:
        time.sleep(1)
    
if __name__ == "__main__":
    main()
