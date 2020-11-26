from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import logging
import time
import argparse
import json


class IoTCoreClient:
    client = None
    
    def __init__(self):
        logger = logging.getLogger("AWSIoTPythonSDK.core")
        logger.setLevel(logging.INFO)
        streamHandler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        streamHandler.setFormatter(formatter)
        logger.addHandler(streamHandler)

    def init(self, host, port, root_ca_path, private_key_path, certificate_path, client_id):
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

        # Connect
        self.client.connect()

    def subscribe(self, topic, callback):
        self.client.subscribe(topic, 1, callback)

    def publish(self, topic, message):
        self.client.publish(topic, message, 1)
        
    def subscribe_shadow_delta(self, thing_name, callback):
        topic = '$aws/things/' + thing_name + '/shadow/update/delta'
        self.client.subscribe(topic, 1, callback)

    def subscribe_shadow_delete_accepted(self, thing_name, callback):
        topic = '$aws/things/' + thing_name + '/shadow/delete/accepted'
        self.client.subscribe(topic, 1, callback)

    def subscribe_shadow_delete_rejected(self, thing_name, callback):
        topic = '$aws/things/' + thing_name + '/shadow/delete/rejected'
        self.client.subscribe(topic, 1, callback)

    def subscribe_shadow_get_accepted(self, thing_name, callback):
        topic = '$aws/things/' + thing_name + '/shadow/get/accepted'
        self.client.subscribe(topic, 1, callback)

    def subscribe_shadow_get_rejected(self, thing_name, callback):
        topic = '$aws/things/' + thing_name + '/shadow/get/rejected'
        self.client.subscribe(topic, 1, callback)

    def subscribe_shadow_update_accepted(self, thing_name, callback):
        topic = '$aws/things/' + thing_name + '/shadow/update/accepted'
        self.client.subscribe(topic, 1, callback)

    def subscribe_shadow_update_rejected(self, thing_name, callback):
        topic = '$aws/things/' + thing_name + '/shadow/update/rejected'
        self.client.subscribe(topic, 1, callback)

    def subscribe_shadow_update_documents(self, thing_name, callback):
        topic = '$aws/things/' + thing_name + '/shadow/update/documents'
        self.client.subscribe(topic, 1, callback)

    def publish_shadow_get_request(self, thing_name):
        topic = '$aws/things/' + thing_name + '/shadow/get'
        self.publish(topic, '')
