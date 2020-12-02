from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import logging
import time
import argparse
import json
import threading
import queue
import asyncio
import shelve
import sys
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
    toybox_mode_standby = 'standby'
    toybox_mode_cleaning = 'cleaning'

    # Shadow Properties name
    shadow_mode = 'mode'
    shadow_weight = 'weight'
    shadow_total_toy_weight = 'total_toy_weight'
    shadow_bgm_path = 'bgm_path'
    shadow_is_bgm_playing = 'is_bmg_playing'
    shadow_sound_effect_path_for_notification = 'sound_effect_path_for_notification'
    shadow_sound_effect_path_for_toy_in = 'sound_effect_path_for_toy_in'
    shadow_sound_effect_path_for_toy_out = 'sound_effect_path_for_toy_out'
    shadow_sound_effect_path_for_start_cleaning = 'sound_effect_path_for_start_cleaning'
    shadow_sound_effect_path_for_end_cleaning = 'sound_effect_path_for_end_cleaning'
    shadow_message_start_cleaning= 'message_start_cleaning'
    shadow_message_end_cleaning= 'message_end_cleaning'
    
    def __init__(self):
        self.iot_core = IoTCoreClient()
        self.iot_core_publish_queue = queue.Queue()
        self.weight_sensor = WeightSensor()
        self.dual_button = DualButton()
        self.bgm_player = Player()
        self.sound_effect_player = Player()
        self.play_sound_queue = queue.Queue()
        self.iot_core_client_id = None
        
        self.mode = None
        self.weight = None
        self.total_toy_weight = None
        self.bgm_path = None
        self.is_bgm_playing = None
        self.sound_effect_path_for_notification = None
        self.sound_effect_path_for_toy_in = None
        self.sound_effect_path_for_toy_out = None
        self.sound_effect_path_for_start_cleaning = None
        self.sound_effect_path_for_end_cleaning = None
        self.message_start_cleaning = None
        self.message_end_cleaning = None
        
    def init(self):
        # Load last memory
        self.mode = self.load_last_memory(self.shadow_mode, self.toybox_mode_standby)
        self.weight = self.load_last_memory(self.shadow_weight, 0)
        self.total_toy_weight = self.load_last_memory(self.shadow_weight, 0)
        self.bgm_path = self.load_last_memory(self.shadow_bgm_path, 'sounds/bgm_maoudamashii_8bit29.mp3')
        self.is_bgm_playing = self.load_last_memory(self.shadow_is_bgm_playing, False)
        self.sound_effect_path_for_notification = self.load_last_memory(self.shadow_sound_effect_path_for_notification, './sounds/se_maoudamashii_onepoint23.mp3')
        self.sound_effect_path_for_toy_in = self.load_last_memory(self.shadow_sound_effect_path_for_toy_in, './sounds/se_maoudamashii_magical29.mp3')
        self.sound_effect_path_for_toy_out = self.load_last_memory(self.shadow_sound_effect_path_for_toy_out, './sounds/se_maoudamashii_magical29.mp3')
        self.sound_effect_path_for_start_cleaning = self.load_last_memory(self.shadow_sound_effect_path_for_start_cleaning, './sounds/se_maoudamashii_magical29.mp3')
        self.sound_effect_path_for_end_cleaning = self.load_last_memory(self.shadow_sound_effect_path_for_end_cleaning , './sounds/se_maoudamashii_magical29.mp3')
        self.message_start_cleaning = self.load_last_memory(self.shadow_message_start_cleaning, 'おもちゃを片付けよう！')
        self.message_end_cleaning = self.load_last_memory(self.shadow_message_end_cleaning, 'すごい！片付けできたね！')
        
        # IoT Core
        logger.info('initialize iot core')        
        self.iot_core_client_id = 'toybox/' + settings.DEVICE_ID
        self.iot_core.init(settings.IOT_CORE_HOST, settings.IOT_CORE_PORT, settings.IOT_CORE_ROOT_CA_PATH, settings.IOT_CORE_PRIVATE_KEY_PATH, settings.IOT_CORE_CERTIFICATE_PATH, self.iot_core_client_id, settings.DEVICE_ID)

        # Iot Core shadows
        self.update_shadow_with_toybox_last_memory()
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
        play_sound_thread = threading.Thread(target=self.play_sound_worker)
        play_sound_thread.start()
        

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
            self.iot_core_publish_shadow_async(self.shadow_mode, self.mode)

    def toybox_is_bgm_playing_handler(self, is_bgm_playing_required):
        if self.is_bgm_playing != is_bgm_playing_required:
            if self.is_bgm_playing == True:
                self.play_sound_async('bgm', self.bgm_path)
            elif self.is_bgm_playing == False:
                self.stop_bgm()
            

    def speech_request_handler(self, request_detail):
        try:
            text_to_speech = request_detail['text']
        except:
            logger.warning('request_detail is invalid')
            return
        self.play_sound_async('text_to_speech', text_to_speech)

    def play_sound_effect_request_handler(self, request_detail):
        try:
            sound_effect_type = request_detail['sound_effect_type']
        except:
            logger.warning('request_detail is invalid')
            return
        if sound_effect_type == 'notification':
            self.play_sound_async('sound_effect', self.sound_effect_path_for_notification)
        
    def set_total_toy_weight_request_handler(self, request_detail):
        self.total_toy_weight  = self.weight
        self.save_last_memory('total_toy_weight', self.total_toy_weight)
        self.iot_core_publish_shadow_async(self.shadow_total_toy_weight, self.total_toy_weight)
        text_to_speech = 'おもちゃの総重量が' + str(self.total_toy_weight) + 'グラムに設定されました'
        self.play_sound_async('sound_effect', self.sound_effect_path_for_notification)
        self.play_sound_async('text_to_speech', text_to_speech)

    def factory_reset_request_handler(self, request_detail):
        logger.info('factory reset')
        self.reset_last_memory()
        sys.exit(0)
        
    def control_request_handler(self, request_type, request_detail):
        if request_type == 'speech':
            self.speech_request_handler(request_detail)
        elif request_type == 'play_sound_effect':
            self.play_sound_effect_handler(request_detail)
        elif request_type == 'set_total_weight':
            self.set_total_toy_weight_request_handler(request_detail)
        elif request_type == 'factory_reset':
            self.factory_reset_request_handler(request_detail)

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
        try:
            changed_shadow_properties = delta['state']
        except:
            logger.warning('invalid data')
            return
        for shadow_prop in changed_shadow_properties:
            print('shadow delta property : ' + shadow_prop)
            if shadow_prop == self.shadow_mode:
                self.toybox_mode_handler(shadow_prop)
            elif shadow_prop == self.shadow_is_bgm_playing:
                self.toybox_is_bgm_playing_handler(shadow_prop)
        
        
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
            self.play_sound_effect(self.sound_effect_path_for_toy_in)
        
    def weight_sensor_worker(self):
        interval = 1
        last_publish_value = -1000
        publish_topic = 'toybox/' + settings.DEVICE_ID + '/sensor/weight'
        while True:
            sensor_val = int(self.weight_sensor.get_value())
            self.weight = sensor_val
            if abs(last_publish_value - sensor_val) > 10:
                diff = sensor_val - last_publish_value
                self.play_sound_effect_with_weight_sensor_changes(sensor_val, diff)
                message = self.create_publish_message_weight_sensor(sensor_val, diff)
                self.iot_core_publish_async(publish_topic, message)
                self.iot_core_publish_shadow_async(self.shadow_weight, int(sensor_val))
                last_publish_value = sensor_val
                logger.info('weight sensor val : ' + str(sensor_val))
            time.sleep(0.1)

            
    def play_bgm(self, path):
        self.bgm_player.loadfile(path)
        self.bgm_player.loop = 0
        self.is_bgm_playing = True
        self.iot_core_publish_shadow_async(self.shadow_is_bgm_playing, self.is_bgm_playing)

    def stop_bgm(self):
        if self.is_bgm_playing == True:
            self.bgm_player.pause()
            self.is_bgm_playing = False
            self.iot_core_publish_shadow_async(self.shadow_is_bgm_playing, self.is_bgm_playing)
            
    def play_sound_effect(self, path):
        self.sound_effect_player.loadfile(path)

            
    def load_last_memory(self, key, default):
        last_memory = shelve.open('toybox_data')
        if key in last_memory:
            ret = last_memory[key]
        else:
            last_memory[key] = default
            ret = default
        last_memory.close()
        return ret
    
    def save_last_memory(self, key, value):
        last_memory = shelve.open('toybox_data')
        last_memory[key] = value
        last_memory.close()

    def reset_last_memory(self):
        last_memory = shelve.open('toybox_data')
        last_memory.clear()
        last_memory.close()

    def update_shadow_with_toybox_last_memory(self):
        last_memory = shelve.open('toybox_data')
        for key in last_memory:
            self.iot_core.update_shadow(key, last_memory[key])

        
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

    def play_sound_async(self, sound_type, sound_detail): #type : 'bgm', 'sound_effect', 'text_to_speech'
        self.play_sound_queue.put([sound_type, sound_detail])
        
    def play_sound_worker(self):
        logger.info('start')
        while True:
            if self.play_sound_queue.empty():
                time.sleep(0.1)
                continue
            else:
                try:
                    request = self.play_sound_queue.get(block=False)
                    sound_type = request[0]
                    sound_detail = request[1]
                    if sound_type == 'text_to_speech':
                        self.download_and_speech_text(sound_detail)
                    elif sound_type == 'bgm':
                        self.play_bgm(sound_detail)
                    elif sound_type == 'sound_effect':
                        playsound(sound_detail)
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
