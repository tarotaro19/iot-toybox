from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import logging
import time
import argparse
import json
import threading
import queue
import asyncio
import shelve
from boto3 import client
from playsound import playsound
from mplayer import Player, CmdPrefix
import settings as settings
from weight_sensor import WeightSensor
from iot_core_client import IoTCoreClient
from dual_button import DualButton

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
    current_weight = None
    total_toy_weightxo = None
    toybox_mode_standby = 'standby'
    toybox_mode_cleaning = 'cleaning'
    toybox_shadow_name_mode = 'mode'
    toybox_shadow_name_weight_sensor = 'weight_sensor'
    toybox_shadow_name_total_toy_weight = 'total_toy_weight'
    bgm_player = None
    is_bgm_playing = False
    sound_effect_player = None
    
    def __init__(self):
        self.mode = self.toybox_mode_standby
        self.iot_core = IoTCoreClient()
        self.iot_core_publish_queue = queue.Queue()
        self.weight_sensor = WeightSensor()
        self.dual_button = DualButton()
        self.bgm_player = Player()
        self.sound_effect_player = Player()
        self.text_to_speech_queue = queue.Queue()
        
    def init(self):
        # Load last memory
        self.total_toy_weight = self.load_last_memory('total_toy_weight')
        if self.total_toy_weight is None:
            self.total_toy_weight = 0
        
        # IoT Core
        logger.info('initialize iot core')        
        self.iot_core_client_id = 'toybox/' + settings.DEVICE_ID
        self.iot_core.init(settings.IOT_CORE_HOST, settings.IOT_CORE_PORT, settings.IOT_CORE_ROOT_CA_PATH, settings.IOT_CORE_PRIVATE_KEY_PATH, settings.IOT_CORE_CERTIFICATE_PATH, self.iot_core_client_id, settings.DEVICE_ID)

        # Iot Core shadows
        self.iot_core.update_shadow(self.toybox_shadow_name_mode, self.mode)
        self.iot_core.update_shadow(self.toybox_shadow_name_total_toy_weight, self.total_toy_weight)
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
        self.iot_core.subscribe(subscribe_topic, self.control_request_callback)

        # Weight sensor
        logger.info('initialize weight sensor')        
        self.weight_sensor.init_sensor(settings.WEIGHT_SENSOR_OUTPUT_PER_GRAM, settings.WEIGHT_SENSOR_OFFSET)
        weight_sensor_thread = threading.Thread(target=self.weight_sensor_worker)
        weight_sensor_thread.start()

        # Button
        self.dual_button.init(self.blue_button_handler, self.red_button_handler)

        # text speech thread
        text_to_speech_thread = threading.Thread(target=self.text_to_speech_worker)
        text_to_speech_thread.start()
        

    def iot_core_publish_async(self, topic, message):
        self.iot_core_publish_queue.put([topic, message])

    def iot_core_publish_shadow_async(self, key, value):
        self.iot_core_publish_queue.put(['shadow', key, value])
        
    def iot_core_publish_message_worker(self):
        logger.info('start')
        while True:
            if self.iot_core_publish_queue.empty():
                time.sleep(0.1)
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
                        self.iot_core.publish(topic, message)
                except:
                    time.sleep(0.1)
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
            self.iot_core_publish_shadow_async(self.toybox_shadow_name_mode, self.mode)

        
    def set_total_toy_weight(self):
        self.total_toy_weight  = self.current_weight
        self.save_last_memory('total_toy_weight', self.total_toy_weight)
        self.iot_core_publish_shadow_async(self.toybox_shadow_name_total_toy_weight, self.total_toy_weight)
        text_to_speech = 'おもちゃの総重量が' + str(self.total_toy_weight) + 'グラムに設定されました'
        self.speech_text_async(text_to_speech)
        
        
    def control_request_handler(self, request_type, request_detail):
        if request_type == 'speech':
            try:
                text_to_speech = request_detail['text']
            except:
                logger.warning('request_detail is invalid')
                return
            self.speech_text_async(text_to_speech)
        elif request_type == 'set_total_weight':
            self.set_total_toy_weight()
            
        
    def control_request_callback(self, client, userdata, message):
        logger.info('from topic: ' + message.topic)
        logger.info('message: ' + str(message.payload))
        try:
            request = json.loads(message.payload)
            request_type = request['type']
            request_detail = request['detail']
        except:
            logger.warning('request is invalid')
            return
        self.control_request_handler(request_type, request_detail)

        
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


    def play_sound_effect_with_weight_sensor_changes(self, sensor_val, diff):
        if self.mode == self.toybox_mode_cleaning and diff > 0:
            self.play_sound_effect('./sounds/se_maoudamashii_magical29.mp3')
        
    def weight_sensor_worker(self):
        interval = 1
        last_publish_value = -1000
        publish_topic = 'toybox/' + settings.DEVICE_ID + '/sensor/weight'
        while True:
            sensor_val = int(self.weight_sensor.get_value())
            self.current_weight = sensor_val
            if abs(last_publish_value - sensor_val) > 10:
                diff = sensor_val - last_publish_value
                self.play_sound_effect_with_weight_sensor_changes(sensor_val, diff)
                message = self.create_publish_message_weight_sensor(sensor_val, diff)
                self.iot_core_publish_async(publish_topic, message)
                self.iot_core_publish_shadow_async('weight_sensor', int(sensor_val))
                last_publish_value = sensor_val
                logger.info('weight sensor val : ' + str(sensor_val))
            time.sleep(0.1)

            
    def play_bgm(self, path):
        self.bgm_player.loadfile(path)
        self.bgm_player.loop = 0
        self.is_bgm_playing= True

    def stop_bgm(self):
        if self.is_bgm_playing == True:
            self.bgm_player.pause()
            self.is_bgm_playing = False
            
    def play_sound_effect(self, path):
        self.sound_effect_player.loadfile(path)

            
    def load_last_memory(self, key):
        last_memory = shelve.open('toybox_data')
        if key in last_memory:
            ret = last_memory[key]
        else:
            ret =  None
        last_memory.close()
        return ret
    
    def save_last_memory(self, key, value):
        last_memory = shelve.open('toybox_data')
        last_memory[key] = value
        last_memory.close()

        
    def create_publish_message_button_pressed(self, value):
        message = {}
        message['time'] = int(time.time())
        message['value'] = value
        return json.dumps(message)
    
    def blue_button_handler(self):
        message = self.create_publish_message_button_pressed('blue')
        publish_topic = 'toybox/' + settings.DEVICE_ID + '/sensor/button'
        self.iot_core_publish_async(publish_topic, message)

    def red_button_handler(self):
        message = self.create_publish_message_button_pressed('red')
        publish_topic = 'toybox/' + settings.DEVICE_ID + '/sensor/button'
        self.iot_core_publish_async(publish_topic, message)

    def create_ssml_text(self, text_to_speech):
        ssml_text = "<speak><prosody volume=\"x-loud\">" + text_to_speech + "</prosody></speak>"
        return ssml_text

    def download_and_speech_text(self, text_to_speech):
        polly = client("polly", region_name=settings.REGION_NAME, aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                       aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

        ssml_text = self.create_ssml_text(text_to_speech)
        response = polly.synthesize_speech(Text = ssml_text, TextType = 'ssml',
                                           OutputFormat = "mp3", VoiceId = "Mizuki")
        file = open("test.mp3", "wb")
        file.write(response["AudioStream"].read())
        file.close()
        playsound("test.mp3")


    def speech_text_async(self, text_to_speech):
        self.text_to_speech_queue.put([text_to_speech])
        
    def text_to_speech_worker(self):
        logger.info('start')
        while True:
            if self.text_to_speech_queue.empty():
                time.sleep(0.1)
                continue
            else:
                try:
                    request = self.text_to_speech_queue.get(block=False)
                    text_to_speech = request[0]
                    self.download_and_speech_text(text_to_speech)
                except:
                    time.sleep(0.1)
                    continue                
        
def main():
    toybox = Toybox()
    toybox.init()
    while True:
        time.sleep(1)
        
if __name__ == "__main__":
    main()
