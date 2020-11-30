#!/usr/bin/python3
import sys
from boto3 import client
from playsound import playsound
import settings as settings

def main():
    text_to_speech = "<speak><prosody volume=\"x-loud\">おはようございます</prosody></speak>"
    polly = client("polly", region_name=settings.REGION_NAME, aws_access_key_id=settings.AWS_ACCESS_KEY_ID, aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
    response = polly.synthesize_speech(
                Text = text_to_speech,
                TextType = 'ssml',
                OutputFormat = "mp3",
                VoiceId = "Mizuki")

    file = open("test.mp3", "wb")
    file.write(response["AudioStream"].read())
    file.close()

    playsound("test.mp3")


if __name__ == "__main__":
    main()
