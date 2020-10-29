# 重量センサ
## ハードウェア
下記を購入
* デジタルロードセル 電子スケール ロードセル計量センサ 重量センサ5KG + HX711 24BIT精密ADモジュール A r d u i n o と互換、ナイロンガイドポストとネジ付き、教育DIY   
https://www.amazon.co.jp/dp/B07JL7NP3F/
## 参考ページ
* デジタルスケールをハック  
https://note.com/izawa/n/n0b4d4866470a
* 重量センサーデータをRaspberryPi3で取得して、GCP Cloud IoT Core/BigQueryに送る方法  
https://qiita.com/shinkoizumi0033/items/c453f33eb5bbd1e1aa6a
* Raspberry piチュートリアル  
https://tutorials-raspberrypi.com/digital-raspberry-pi-scale-weight-sensor-hx711/
* raspberry piとhx711を使った重量測定器  
https://qiita.com/todateman/items/9fb3c251a1eb720efab1
## サンプルソフト
* tatoberi  
HX711を扱うためのサンプルがある　　
https://github.com/tatobari/hx711py
## お試し動作確認
* Raspberry pi の接続先  
  - 電源は5Vらしい
  - example.py の hx711(5,6) というのがGPIOの番号を表してそう
  - hx711.py のクラスのコンストラクタで 下記のように定義されているので,　　
  dout=5, pd_sck=6に接続すれば良いっぽい  
  ```python
   def __init__(self, dout, pd_sck, gain=128):
        self.PD_SCK = pd_sck
        self.DOUT = dout
  ```
  - 赤:Vcc, 茶色:SCK->GPIO6, 白:DT->GPIO5, 黒: GND
    (GPIO配置 : https://www.raspberrypi.org/documentation/usage/gpio/)
* キャリブレーション
(出力)/(gram) を算出して、 hx.set_reference_unit()の関数に突っ込むらしい
  - example.py の 下記をコメントアウト
  ```
  hx.set_reference_unit(referenceUnit) 
  ```
  - 重量がわかっているものを載せて出力値を見る  
  iPhoneXR(194g)を載せてみる  (最初は載せないで起動して、その後に載せる)  
  ⇒ だいたい 94050 くらいか
    ```console
    pi@suzuki:~/work/iot/sensors/weight_scale/ref/hx711py$ python3 example.py 
    Tare done! Add weight now...
    19.77777777778101
    4.7777777777810115
    -17.22222222221899
    -3.2222222222189885
    -17.22222222221899
    -30.22222222221899
    30280.77777777778
    94036.77777777778
    94001.77777777778
    94015.77777777778
    94070.77777777778
    94041.77777777778
    94059.77777777778
    94084.77777777778
    94043.77777777778
    94015.77777777778
    94057.77777777778
    94079.77777777778
    94039.77777777778
    94067.77777777778
    94050.77777777778
    94019.77777777778
    94056.77777777778
    94020.77777777778
    ```
  - (出力)/(gram)を算出  
  94050/194 = 485
  - hx.set_reference_unit()に設定  
    ```python
    hx.set_reference_unit(485)
    ``` 
* offsetの設定  
このサンプルのユースケースとしては、起動時に何も載っていないという前提で起動時の重量はoffsetと無視するようにしている. 今回のユースケースでは起動時におもちゃ箱の重さを図りたいので、このoffsetを空のおもちゃ箱が載っている状態を "0" として設定する必要がある.  
  - example.py の hx.tare()の中で offset値設定のための現状の値のread(15回読み込んで平均する),その値をoffsetとして設定するということを実施している
  - 空の状態のデフォルト値をreadして、それをoffset設定すれば良い  
  イメージとしては下記のように空の状態でoffset値を取得しておいて、それを記録して, set_offset() しておく. これで起動時にiPhoneが載っていても重さが図ることができるようになった  
    ```python
    #offset = hx.read_average(15)#print ('average :' + str(average)
    offset = -109138
    hx.set_offset(offset)
    ``` 
