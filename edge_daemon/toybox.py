from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import logging
import time
import argparse
import json
import threading
import queue
import asyncio
from boto3 import client
from playsound import playsound
from mplayer import Player, CmdPrefix
import settings as settings
from weight_sensor import WeightSensor
from iot_core_client import IoTCoreClient

### Logger
logger = logging.getLogger("Toybox")
logger.setLevel(logging.DEBUG)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s\t%(levelname)s\t%(name)s\t%(funcName)s\t%(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

class Toybox:
    iot_core = None
    iot_core_client_id = None
    iot_core_publish_queue = None
    mode = None
    toybox_mode_standby = 'standby'
    toybox_mode_cleaning = 'cleaning'
    bgm_player = None
    is_bgm_playing = False
    sound_effect_player = None
    
    def __init__(self):
        self.mode = self.toybox_mode_standby
        self.iot_core = IoTCoreClient()
        self.iot_core_publish_queue = queue.Queue()
        self.weight_sensor = WeightSensor()
        self.bgm_player = Player()
        self.sound_effect_player = Player()
        
    def init(self):
        # IoT Core
        logger.info('initialize iot core')        
        self.iot_core_client_id = 'toybox/' + settings.DEVICE_ID
        self.iot_core.init(settings.IOT_CORE_HOST, settings.IOT_CORE_PORT, settings.IOT_CORE_ROOT_CA_PATH, settings.IOT_CORE_PRIVATE_KEY_PATH, settings.IOT_CORE_CERTIFICATE_PATH, self.iot_core_client_id, settings.DEVICE_ID)

        # Iot Core shadows
        self.iot_core.update_shadow('mode', self.mode)
        self.iot_core.subscribe_shadow_delta(self.shadow_delta_callback)
        self.iot_core.subscribe_shadow_delete_accepted(self.shadow_common_callback)
        self.iot_core.subscribe_shadow_delete_rejected(self.shadow_common_callback)
        self.iot_core.subscribe_shadow_get_accepted(self.shadow_get_accepted_callback)
        self.iot_core.subscribe_shadow_get_rejected(self.shadow_common_callback)
        self.iot_core.subscribe_shadow_update_accepted(self.shadow_common_callback)
        self.iot_core.subscribe_shadow_update_rejected(self.shadow_common_callback)
        self.iot_core.subscribe_shadow_update_documents(self.shadow_common_callback)
        self.iot_core.publish_shadow_get_request()
        iot_core_publish_message_thread = threading.Thread(target=self.iot_core_publish_message_worker)
        iot_core_publish_message_thread.start()

        # subscribe control request topic
        subscribe_topic = 'toybox/' + settings.DEVICE_ID + '/control'
        self.iot_core.subscribe(subscribe_topic, self.subscription_callback)

        # Weight sensor
        logger.info('initialize weight sensor')        
        self.weight_sensor.init_sensor(settings.WEIGHT_SENSOR_OUTPUT_PER_GRAM, settings.WEIGHT_SENSOR_OFFSET)
        weight_sensor_thread = threading.Thread(target=self.weight_sensor_worker)
        weight_sensor_thread.start()

        
    def iot_core_publish_message_worker(self):
        logger.info('start')
        while True:
            if self.iot_core_publish_queue.empty():
                continue
            else:
                try:
                    request = self.iot_core_publish_queue.get(block=False)
                    if request[0] == 'shadow':
                        key = request[1]
                        value = request[2]
                        self.iot_core.update_shadow(key, value)
                    else:
                        topic = request[0]
                        message = request[1]
                        self.iot_core.publosh(topic, message)
                except:
                    continue                

                
    def toybox_mode_handler(self, mode_required):
        if self.mode != mode_required:
            logger.info('try to change mode to ' + mode_required)
            self.mode = mode_required
            if self.mode == self.toybox_mode_cleaning:
                self.play_bgm('sounds/bgm_maoudamashii_8bit29.mp3')
            elif self.mode == self.toybox_mode_standby:
                self.stop_bgm()
            else:
                logger.warning("mode_required is not valid")
                return
            self.iot_core_publish_queue.put(['shadow', 'mode', self.mode])
            #self.iot_core.update_shadow('mode', self.mode)

            
    def downloadAndSpeechText(self, textToSpeech):
        polly = client("polly", region_name=settings.REGION_NAME, aws_access_key_id=settings.AWS_ACCESS_KEY_ID, aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
        response = polly.synthesize_speech(Text = textToSpeech, OutputFormat = "mp3", VoiceId = "Mizuki")

        file = open("test.mp3", "wb")
        file.write(response["AudioStream"].read())
        file.close()
        playsound("test.mp3")

        
    def subscription_callback(self, client, userdata, message):
        logger.info('from topic: ' + message.topic)
        logger.info('message: ' + str(message.payload))

        request = json.loads(message.payload)
        requestType = request['type']
        requestDetail = request['detail']
        logger.info ('requestType: ' + requestType)
        logger.info ('requestDetail: ' + str(requestDetail))
        self.downloadAndSpeechText(requestDetail['text'])

        
    def shadow_delta_callback(self, client, userdata, message):
        logger.info('from topic: ' + message.topic)
        logger.info('message: ' + str(message.payload))
        delta = json.loads(message.payload)
        try :
            mode_required = delta['state']['mode']
        except:
            logger.error('mode property is not set')
            return
        self.toybox_mode_handler(mode_required)
        
    def shadow_get_accepted_callback(self, client, userdata, message):
        logger.info('from topic: ' + message.topic)
        logger.info('message: ' + str(message.payload))
        delta = json.loads(message.payload)
        try:
            mode_required = delta['state']['desired']['mode']
        except:
            logger.error('mode property is not set')
            return
        ### ToDo implement mode handler

        
    def shadow_common_callback(self, client, userdata, message):
        #logger.info('from topic: ' + message.topic)
        #logger.info('message: ' + str(message.payload))
        msg = json.loads(message.payload)

        
    def create_publish_message_weight_sensor(self, value, diff):
        message = {}
        message['time'] = int(time.time())
        message['value'] = int(value)
        message['diff'] = int(diff)
        return json.dumps(message)

    
    def weight_sensor_worker(self):
        interval = 1
        last_publish_value = -1000
        publish_topic = 'toybox/' + settings.DEVICE_ID + '/sensor/weight'
        while True:
            sensor_val = int(self.weight_sensor.get_value())
            if abs(last_publish_value - sensor_val) > 10:
                diff = sensor_val - last_publish_value
                message = self.create_publish_message_weight_sensor (sensor_val, diff)
                self.iot_core.publish(publish_topic, message)
                self.iot_core.update_shadow('weight_sensor', int(sensor_val))
                last_publish_value = sensor_val
                logger.info('weight sensor val : ' + str(sensor_val))
            time.sleep(1)

            
    def play_bgm(self, path):
        self.bgm_player.loadfile(path)
        self.bgm_player.loop = 0
        self.is_bgm_playing= True

        
    def stop_bgm(self):
        if self.is_bgm_playing == True:
            self.bgm_player.pause()
            self.is_bgm_playing = False

        
def main():
    toybox = Toybox()
    toybox.init()
    while True:
        time.sleep(1)
        
if __name__ == "__main__":
    main()
