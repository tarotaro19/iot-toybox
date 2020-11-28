from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import logging
import time
import argparse
import json

logger = logging.getLogger("IoTCoreClient")
logger.setLevel(logging.INFO)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

class IoTCoreClient:
    client = None
    thing_name = None
    
    def __init__(self):
        return

    def init(self, host, port, root_ca_path, private_key_path, certificate_path, client_id, thing_name):
        # Init AWSIoTMQTTClient
        self.client = AWSIoTMQTTClient(client_id)
        self.client.configureEndpoint(host, port)
        self.client.configureCredentials(root_ca_path, private_key_path, certificate_path)

        # AWSIoTMQTTClient connection configuration
        self.client.configureAutoReconnectBackoffTime(1, 32, 20)
        self.client.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
        self.client.configureDrainingFrequency(2)  # Draining: 2 Hz
        self.client.configureConnectDisconnectTimeout(10)  # 10 sec
        self.client.configureMQTTOperationTimeout(5)  # 5 sec

        # for shadows
        self.thing_name = thing_name
        
        # Connect
        self.client.connect()

    def subscribe(self, topic, callback):
        self.client.subscribe(topic, 1, callback)

    def publish(self, topic, message):
        logger.info('publish - topic:' + topic + ', message' + message)
        self.client.publish(topic, message, 1)

    ### Shadows
    def subscribe_shadow_delta(self, callback):
        topic = '$aws/things/' + self.thing_name + '/shadow/update/delta'
        self.client.subscribe(topic, 1, callback)

    def subscribe_shadow_delete_accepted(self, callback):
        topic = '$aws/things/' + self.thing_name + '/shadow/delete/accepted'
        self.client.subscribe(topic, 1, callback)

    def subscribe_shadow_delete_rejected(self, callback):
        topic = '$aws/things/' + self.thing_name + '/shadow/delete/rejected'
        self.client.subscribe(topic, 1, callback)

    def subscribe_shadow_get_accepted(self, callback):
        topic = '$aws/things/' + self.thing_name + '/shadow/get/accepted'
        self.client.subscribe(topic, 1, callback)

    def subscribe_shadow_get_rejected(self, callback):
        topic = '$aws/things/' + self.thing_name + '/shadow/get/rejected'
        self.client.subscribe(topic, 1, callback)

    def subscribe_shadow_update_accepted(self, callback):
        topic = '$aws/things/' + self.thing_name + '/shadow/update/accepted'
        self.client.subscribe(topic, 1, callback)

    def subscribe_shadow_update_rejected(self, callback):
        topic = '$aws/things/' + self.thing_name + '/shadow/update/rejected'
        self.client.subscribe(topic, 1, callback)

    def subscribe_shadow_update_documents(self, callback):
        topic = '$aws/things/' + self.thing_name + '/shadow/update/documents'
        self.client.subscribe(topic, 1, callback)

    def publish_shadow_get_request(self):
        topic = '$aws/things/' + self.thing_name + '/shadow/get'
        self.publish(topic, '')

    def update_shadow(self, key, value):
        topic = '$aws/things/' + self.thing_name + '/shadow/update'
        message = {}
        reported = {}
        reported[key] = value
        message = {"state": {"reported": reported}}
        self.publish(topic, json.dumps(message))
        
