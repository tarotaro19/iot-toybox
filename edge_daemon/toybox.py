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
from mfrc522 import SimpleMFRC522

### Logger
logger = logging.getLogger("Toybox")
logger.setLevel(logging.INFO)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s\t%(levelname)s\t%(name)s\t%(funcName)s\t%(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

class ToyboxProperty:
    def __init__(self, name, default_value):
        self.name = name
        self.value = default_value
        self.default_value = default_value

class ToyboxProperties:
    def __init__(self):
        self.mode = ToyboxProperty('mode', 'standby')
        self.weight = ToyboxProperty('weight', 0)
        self.total_toy_weight = ToyboxProperty('total_toy_weight', 0)
        self.bgm_path = ToyboxProperty('bgm_path', 'sounds/bgm_maoudamashii_8bit29.mp3')
        self.is_bgm_playing = ToyboxProperty('is_bgm_playing', False)
        self.rfid_detection_sound = ToyboxProperty('rfid_detection_sound', True)
        self.sound_effect_path_for_notification = ToyboxProperty('sound_effect_path_for_notification', './sounds/se_maoudamashii_onepoint23.mp3')
        self.sound_effect_path_for_nogood = ToyboxProperty('sound_effect_path_for_nogood', './sounds/se_maoudamashii_onepoint14.mp3')
        self.sound_effect_path_for_good = ToyboxProperty('sound_effect_path_for_good', './sounds/se_maoudamashii_onepoint15.mp3')
        self.sound_effect_path_for_toy_in = ToyboxProperty('sound_effect_path_for_toy_in', './sounds/se_maoudamashii_magical29.mp3')
        self.sound_effect_path_for_toy_out = ToyboxProperty('sound_effect_path_for_toy_out', './sounds/se_maoudamashii_magical29.mp3')
        self.sound_effect_path_for_rfid_detection = ToyboxProperty('sound_effect_path_for_rfid_detection', './sounds/se_maoudamashii_onepoint25.mp3')
        
class Toybox:
    toybox_mode_standby = 'standby'
    toybox_mode_cleaning = 'cleaning'
    
    def __init__(self):
        self.properties = ToyboxProperties()
        self.iot_core = IoTCoreClient()
        self.iot_core_publish_queue = queue.Queue()
        self.weight_sensor = WeightSensor()
        self.dual_button = DualButton()
        self.bgm_player = Player()
        self.sound_effect_player = Player()
        self.play_sound_queue = queue.Queue()
        self.iot_core_client_id = None
        self.is_loading_properties_finished = False
        
    def init(self):
        logger.debug('')
        
        # IoT Core
        logger.info('initialize iot core')        
        self.iot_core_client_id = 'toybox/' + settings.DEVICE_ID
        self.iot_core.init(settings.IOT_CORE_HOST, settings.IOT_CORE_PORT, settings.IOT_CORE_ROOT_CA_PATH, settings.IOT_CORE_PRIVATE_KEY_PATH, settings.IOT_CORE_CERTIFICATE_PATH, self.iot_core_client_id, settings.DEVICE_ID)

        # get shadow and initialize properties
        self.iot_core.subscribe_shadow_get_accepted(self.shadow_get_accepted_callback)
        self.iot_core.subscribe_shadow_get_rejected(self.shadow_get_rejected_callback)
        self.iot_core.publish_shadow_get_request()
        self.wait_loading_properties()
        self.iot_core.unsubscribe_shadow_get_accepted()
        logger.debug('weight : ' + str(self.properties.weight.value))

        # Iot Core shadows
        self.iot_core.subscribe_shadow_delta(self.shadow_delta_callback)
        self.iot_core.subscribe_shadow_delete_accepted(self.shadow_common_callback)
        self.iot_core.subscribe_shadow_delete_rejected(self.shadow_common_callback)
        self.iot_core.subscribe_shadow_update_accepted(self.shadow_common_callback)
        self.iot_core.subscribe_shadow_update_rejected(self.shadow_common_callback)
        self.iot_core.subscribe_shadow_update_documents(self.shadow_common_callback)
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

        # RFID reader thread
        rfid_reader_thread = threading.Thread(target=self.rfid_reader_worker)
        rfid_reader_thread.start()

    def wait_loading_properties(self):
        logger.info('')
        while True:
            if self.is_loading_properties_finished == True:
                break
            time.sleep(0.1)
        logger.info('wait loading properties end')

    def iot_core_publish_async(self, topic, message):
        logger.debug('')
        self.iot_core_publish_queue.put([topic, message])

    def iot_core_publish_shadow_async(self, key, value):
        logger.debug('')
        self.iot_core_publish_queue.put(['shadow', key, value])
        
    def iot_core_publish_message_worker(self):
        logger.debug('')
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
        logger.debug('')
        if self.properties.mode.value != mode_required:
            self.update_property(self.properties.mode, mode_required)

    def toybox_is_bgm_playing_handler(self, is_bgm_playing_required):
        logger.debug('')
        if self.properties.is_bgm_playing.value != is_bgm_playing_required:
            if is_bgm_playing_required == True:
                self.play_sound_async('bgm', self.properties.bgm_path.value)
            elif is_bgm_playing_required == False:
                self.stop_bgm()
            

    def speech_request_handler(self, request_detail):
        logger.debug('')
        try:
            text_to_speech = request_detail['text']
        except:
            logger.warning('request_detail is invalid')
            return
        self.play_sound_async('text_to_speech', text_to_speech)

    def play_sound_effect_request_handler(self, request_detail):
        logger.debug('')
        try:
            sound_effect_type = request_detail['sound_effect_type']
        except:
            logger.warning('request_detail is invalid')
            return
        if sound_effect_type == 'notification':
            self.play_sound_async('sound_effect', self.properties.sound_effect_path_for_notification.value)
        elif sound_effect_type == 'nogood':
            self.play_sound_async('sound_effect', self.properties.sound_effect_path_for_nogood.value)
        elif sound_effect_type == 'good':
            self.play_sound_async('sound_effect', self.properties.sound_effect_path_for_good.value)
        
    def set_total_toy_weight_request_handler(self, request_detail):
        logger.debug('')
        current_weight = int(self.weight_sensor.get_value())
        self.update_property(self.properties.total_toy_weight, current_weight)

        text_to_speech = 'おもちゃの総重量が' + str(self.properties.total_toy_weight.value) + 'グラムに設定されました'
        self.play_sound_async('sound_effect', self.properties.sound_effect_path_for_notification.value)
        self.play_sound_async('text_to_speech', text_to_speech)
        
    def control_request_handler(self, request_type, request_detail):
        logger.debug('')
        if request_type == 'speech':
            self.speech_request_handler(request_detail)
        elif request_type == 'play_sound_effect':
            self.play_sound_effect_request_handler(request_detail)
        elif request_type == 'set_total_weight':
            self.set_total_toy_weight_request_handler(request_detail)

    def control_request_callback(self, client, userdata, message):
        logger.debug('')
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

    def shadow_delta_callback_inner(self,shadow_delta_properties):
        for prop_name in shadow_delta_properties:
            if prop_name == self.properties.mode.name:
                self.toybox_mode_handler(shadow_delta_properties[prop_name])
            elif prop_name == self.properties.is_bgm_playing.name:
                self.toybox_is_bgm_playing_handler(shadow_delta_properties[prop_name])
        
    def shadow_delta_callback(self, client, userdata, message):
        logger.debug('')
        logger.info('from topic: ' + message.topic)
        logger.info('message: ' + str(message.payload))
        delta = json.loads(message.payload)
        try:
            shadow_delta_properties = delta['state']
        except:
            logger.warning('invalid data')
            return
        self.shadow_delta_callback_inner(shadow_delta_properties)
        
    def shadow_get_accepted_callback(self, client, userdata, message):
        logger.debug('')
        logger.info('from topic: ' + message.topic)
        logger.info('message: ' + str(message.payload))
        if self.is_loading_properties_finished == True:
            return
        shadow = json.loads(message.payload)
        
        try:
            shadow_reported_proiperties = shadow['state']['reported']
        except:
            logger.error('property is not set')
            shadow_reported_proiperties = {}
        
        for prop in self.properties.__dict__.values():
            if prop.name in shadow_reported_proiperties:
                logger.debug('get properties from shadow : ' + prop.name)
                prop.value = shadow_reported_proiperties[prop.name]
            else:
                logger.debug('update properties to shadow : ' + prop.name)
                self.update_property(prop, prop.value)
        self.is_loading_properties_finished = True

    def shadow_get_rejected_callback(self, client, userdata, message):
        logger.error("error!!! can't get shadow")
        
    def shadow_common_callback(self, client, userdata, message):
        logger.debug('')
        #logger.info('from topic: ' + message.topic)
        #logger.info('message: ' + str(message.payload))
        msg = json.loads(message.payload)

        
    def create_publish_message_weight_sensor(self, value, diff):
        logger.debug('')
        message = {}
        message['time'] = int(time.time())
        message['value'] = int(value)
        message['diff'] = int(diff)
        return json.dumps(message)


    def play_sound_effect_with_weight_sensor_changes(self, sensor_val, diff):
        logger.debug('')
        if self.properties.mode.value == self.toybox_mode_cleaning and diff > 0:
            self.play_sound_effect(self.properties.sound_effect_path_for_toy_in.value)
        
    def weight_sensor_worker(self):
        logger.debug('')
        last_publish_value = self.properties.weight.value
        publish_topic = 'toybox/' + settings.DEVICE_ID + '/sensor/weight'
        while True:
            sensor_val = int(self.weight_sensor.get_value())
            if abs(last_publish_value - sensor_val) > 3:
                diff = sensor_val - last_publish_value
                self.play_sound_effect_with_weight_sensor_changes(sensor_val, diff)
                message = self.create_publish_message_weight_sensor(sensor_val, diff)
                self.iot_core_publish_async(publish_topic, message)
                self.update_property(self.properties.weight, sensor_val)
                last_publish_value = sensor_val
                logger.info('weight sensor val : ' + str(sensor_val))
            time.sleep(0.5)

            
    def play_bgm(self, path):
        logger.debug('')
        if self.properties.is_bgm_playing.value == False:
            self.bgm_player.loadfile(path)
            self.bgm_player.loop = 0
            self.update_property(self.properties.is_bgm_playing, True)

    def stop_bgm(self):
        logger.debug('')
        if self.properties.is_bgm_playing.value == True:
            self.bgm_player.pause()
            self.update_property(self.properties.is_bgm_playing, False)
            
    def play_sound_effect(self, path):
        logger.debug('')
        self.sound_effect_player.loadfile(path)

    def update_shadow_with_properties(self, toybox_properties):
        logger.debug('')
        for prop in toybox_properties.__dict__.values():
            self.iot_core.update_shadow(prop.name, prop.value)

    def update_property(self, prop, value):
        logger.debug('')
        prop.value = value
        self.iot_core_publish_shadow_async(prop.name, prop.value)
        
    def create_publish_message_button_pressed(self, value):
        logger.debug('')
        message = {}
        message['time'] = int(time.time())
        message['value'] = value
        return json.dumps(message)
    
    def blue_button_handler(self):
        logger.debug('')
        message = self.create_publish_message_button_pressed('blue')
        publish_topic = 'toybox/' + settings.DEVICE_ID + '/sensor/button'
        self.iot_core_publish_async(publish_topic, message)

    def red_button_handler(self):
        logger.debug('')
        message = self.create_publish_message_button_pressed('red')
        publish_topic = 'toybox/' + settings.DEVICE_ID + '/sensor/button'
        self.iot_core_publish_async(publish_topic, message)

    def create_ssml_text(self, text_to_speech):
        logger.debug('')
        ssml_text = "<speak><prosody volume=\"x-loud\">" + text_to_speech + "</prosody></speak>"
        return ssml_text

    def download_and_speech_text(self, text_to_speech):
        logger.debug('')
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
        logger.debug('sound_type :' + sound_type + ', sound_detail : ' + sound_detail)
        self.play_sound_queue.put([sound_type, sound_detail])
        
    def play_sound_worker(self):
        logger.debug('')
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

    def create_publish_message_rfid(self, uid, text):
        logger.debug('')
        message = {}
        message['time'] = int(time.time())
        message['uid'] = uid
        message['text'] = text
        return json.dumps(message)
    
    def rfid_reader_worker(self):
        logger.debug('')
        reader = SimpleMFRC522()
        publish_topic = 'toybox/' + settings.DEVICE_ID + '/sensor/rfid'
        
        while True:
            try:
                uid, text = reader.read()
                logger.info('UID:' + str(uid) +  ', Text:' + text)
                message = self.create_publish_message_rfid(str(uid), text)
                self.iot_core_publish_async(publish_topic, message)
                if self.properties.rfid_detection_sound.value == True:
                    self.play_sound_async('sound_effect', self.properties.sound_effect_path_for_rfid_detection.value)
                time.sleep(2)
            except:
                logger.error('error')
                time.sleep(0.5)
        
def main():
    toybox = Toybox()
    toybox.init()
    while True:
        time.sleep(1)
        
if __name__ == "__main__":
    main()
