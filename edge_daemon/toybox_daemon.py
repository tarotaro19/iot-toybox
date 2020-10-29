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

# Custom MQTT message callback
def customCallback(client, userdata, message):
    print("Received a new message: ")
    print(message.payload)
    print("from topic: ")
    print(message.topic)
    print("--------------\n\n")

    request = json.loads(message.payload)
    requestType = request['type']
    requestDetail = request['detail']
    print ('requestType: ' + requestType)
    print ('requestDetail: ' + str(requestDetail))
    downloadAndSpeechText(requestDetail['text'])


# Read in command-line parameters
parser = argparse.ArgumentParser()
parser.add_argument("-e", "--endpoint", action="store", required=True, dest="host", help="Your AWS IoT custom endpoint")
parser.add_argument("-r", "--rootCA", action="store", required=True, dest="rootCAPath", help="Root CA file path")
parser.add_argument("-c", "--cert", action="store", dest="certificatePath", help="Certificate file path")
parser.add_argument("-k", "--key", action="store", dest="privateKeyPath", help="Private key file path")
parser.add_argument("-p", "--port", action="store", dest="port", type=int, help="Port number override")
parser.add_argument("-id", "--clientId", action="store", dest="clientId", default="basicPubSub",
                    help="Targeted client id")
parser.add_argument("-M", "--message", action="store", dest="message", default="Hello World!",
                    help="Message to publish")

args = parser.parse_args()
host = args.host
root_ca_path = args.rootCAPath
certificate_path = args.certificatePath
private_key_path = args.privateKeyPath
clientId = args.clientId


def init_weight_sensor(weight_sensor):
    output_per_gram = 485
    offset = -109138
    weight_sensor.init_sensor(output_per_gram, offset)

def weight_sensor_worker(weight_sensor, iot_core):
    interval = 1
    while True:
        sensor_val = weight_sensor.get_value()
        print('[weight_sensor_thread] sensor_val : ' + str(sensor_val))
        time.sleep(1)


def main():
    port = 8883
    publishTopic = 'toybox/' + clientId + '/sensor/temperature'
    subscribeTopic = 'toybox/' + clientId + '/control'
    iotCoreConnectionClientId = 'toybox/' + clientId

    #IoT core
    iot_core = IoTCoreClient()
    iot_core.init(host, port, root_ca_path, private_key_path, certificate_path, iotCoreConnectionClientId)
    
    #weight sensor
    test = 'test'
    weight_sensor = WeightSensor()
    init_weight_sensor(weight_sensor)
    weight_sensor_thread = threading.Thread(target=weight_sensor_worker, args=(weight_sensor, test))
    weight_sensor_thread.start()

    '''
    # Configure logging
    logger = logging.getLogger("AWSIoTPythonSDK.core")
    logger.setLevel(logging.DEBUG)
    streamHandler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    streamHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)


    # Init AWSIoTMQTTClient
    myAWSIoTMQTTClient = None
    myAWSIoTMQTTClient = AWSIoTMQTTClient(iotCoreConnectionClientId)
    myAWSIoTMQTTClient.configureEndpoint(host, port)
    myAWSIoTMQTTClient.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

    # AWSIoTMQTTClient connection configuration
    myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
    myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
    myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
    myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
    myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec
    '''


    # Init Sensors
    
    
    
    
    print("loop start")
    # Connect and subscribe to AWS IoT
    #myAWSIoTMQTTClient.connect()
    iot_core.subscribe(subscribeTopic, customCallback)
    #myAWSIoTMQTTClient.subscribe(subscribeTopic, 1, customCallback)
    time.sleep(2)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@end")
    
    # Publish to the same topic in a loop forever
    loopCount = 0
    while True:
        message = {}
        message['message'] = args.message
        message['sequence'] = loopCount
        messageJson = json.dumps(message)
        '''
        myAWSIoTMQTTClient.publish(publishTopic, messageJson, 1)
        print('Published topic %s: %s\n' % (publishTopic, messageJson))
        '''
        loopCount += 1
        time.sleep(1)
    
if __name__ == "__main__":
    main()
