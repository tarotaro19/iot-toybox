# edge daemon
Raspberry pi側のdaemonプロセス

# 事前準備
* AWSのPythonライブラリをインストール  
下記を参照  
https://github.com/aws/aws-iot-device-sdk-python#installation  
  ```console
  $ pip3 install AWSIoTPythonSDK
  ```
* IoT Core接続用の秘匿情報をcertディレクトリ配下に配置する  
* settings.pyを作成  
レポジトリ中のものは暗号化されているが下記の内容で作成する
  ```python
  ### DeviceID
  DEVICE_ID = 'grouph-toybox-*****'
  
  ### IoT Core
  IOT_CORE_HOST = '*****.iot.ap-northeast-1.amazonaws.com'
  IOT_CORE_PORT = 8883
  IOT_CORE_ROOT_CA_PATH = './cert/root-CA.crt'
  IOT_CORE_CERTIFICATE_PATH = './cert/*****.pem.crt'
  IOT_CORE_PRIVATE_KEY_PATH = './cert/*****.private.key'
  
  ### Weight Sensor
  WEIGHT_SENSOR_OUTPUT_PER_GRAM = *****
  WEIGHT_SENSOR_OFFSET = *****
  
  ### AWS
  REGION_NAME = 'ap-*******'
  AWS_ACCESS_KEY_ID = '*****'
  AWS_SECRET_ACCESS_KEY = '*****'
  ```
# 実行
```console
$ python3 toybox_daemon.py
```
