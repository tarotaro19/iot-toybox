# edge daemon
Raspberry pi側のdaemonプロセス

# 事前準備
## pythonのライブラリ等
* AWS    
下記を参照  
https://github.com/aws/aws-iot-device-sdk-python#installation  
  ```console
  $ pip3 install AWSIoTPythonSDK
  ```
* mplayer  
  ```console
  $ sudo apt install mplayer
  $ pip3 install mplayer.py
  ```
* その他諸々  
  ```console
  $ pip3 install playsound boto3
  ```

## IoT Core接続用の秘匿情報をcertディレクトリ配下に配置する  
certフォルダの配下に配置する. ファイル名は下記のsettings.pyで設定する
## settings.pyを作成
諸々の設定情報を格納したファイルを作成する
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
$ python3 toybox.py
```

# ボタン
下記のものを購入  (M5stack用デュアルボタンユニット)  
https://www.switch-science.com/catalog/4048/  
Amazonでも購入できるが、switch science の方が数百円安かった  
## 接続
* 参照  
公式ページに回路図がある.  
https://docs.m5stack.com/#/en/unit/dual_button?id=schematic  
押下時に GNDになって、定常時は5Vに接続すれば 5 x 2/3 で 3.3Vになりそう
* raspberry-pi側の接続先  
VCC 5V, GND, GPIO23(青ボタン), GPIO24(赤ボタン) を使うことにする
  
# Tips
* IoT coreライブラリ  
IoT Coreのデバイス側の実装に関しては下記のサンプルなどを参照  
https://github.com/aws/aws-iot-device-sdk-python
