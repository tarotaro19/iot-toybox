# Pollyテスト
## 事前準備
* gstreamer  
aspbery pi での音声再生のために、playsoundというpythonライブラリを利用したが、Gst-1.0がないというエラー.  
下記でgstreamerをインストールすることで回避できた.  
  ```console
  $ sudo apt-get install gstreamer-1.0
  ```
* boto3, playsound
  ```console
  $ pip3 install boto3 playsound
  ```
## settings.pyの作成
下記の内容でsettings.py というファイルを作成する(このレポジトリでは暗号化してあるので各自で作成必要)
```python
REGION_NAME = 'ap-northeast-***'
AWS_ACCESS_KEY_ID = '*****'
AWS_SECRET_ACCESS_KEY = '*****'
```

## 実行
```python
$pytho3 polly_test.py
```

## その他
* スピーカーの接続
下記を参考にした  
https://tomosoft.jp/design/?p=33680
