# RFID reader
RC-522 というRFID　readerを利用する
## 参考
* RaspberryPi で NFC RFID-RC522 を Python3 で使う  
https://qiita.com/nanbuwks/items/c502ba880fbb93f522b3  
*  mxgxw/MFRC522-python  (ここから色々なプロジェクトがforkさてれいるらしい)  
https://github.com/mxgxw/MFRC522-python
*  pimylifeup/MFRC522-python (これを使うpip でmfrc522 でインストールできる)  
https://github.com/pimylifeup/MFRC522-python  
## 準備
* 配線  
右記ページに載っている https://github.com/mxgxw/MFRC522-python#pins  
RC522 -> Raspberry pi
  - SDA (Serial Data Signal) -> 24 (GPIO8)
  - SCK (Serial Clock) -> 23 (GPIO11 SCLK)
  - MOSI (Master Out Slave In) -> 19 (GPIO10 MOSI) 
  - MISO (Master In Slave Out) -> 21 (GPIO9 MISO) 
  - IRQ (Interrupt Request) -> 不要
  - GND -> 25 (場所は任意)
  - RST -> 22 (GPIO25)
  - 3.3v -> 17 (場所は任意)
* SPIの有効化
  ```console
   $ sudo raspi-config 
     -> 5 Interfacing Options  Configure connections to peripherals 
      -> P4 SPI         Enable/Disable automatic loading of SPI kernel module
     設定後に再起動を実施する
  ```
* mfrc522　pythonモジュールのインストール
```console
$ sudo pip3 install mfrc522
```
## テスト
read or write は中のコードを書き換えて切り替え
```console
$ python3 rfid_reader.py
```
