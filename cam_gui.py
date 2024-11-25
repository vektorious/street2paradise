from gpiozero import Button
from picamera2 import Picamera2, Preview
from libcamera import Transform
from time import gmtime, strftime, sleep
from guizero import App, Text, Picture, TextBox, Box, Slider, PushButton
from PIL import Image
import base64
import os
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import config

sender_email = config.sender_email
sender_password = config.sender_password
recipient_email = config.recipient_email
api_key = config.api_key


output = ""
output_converted = ""
latest_photo = "output/latest.gif"
latest_converted = "output/latest_converted.gif"
taking_picture = False
preview_running = False
convert_running = False
engine_id = "stable-diffusion-v1-6"
api_host = os.getenv("API_HOST", "https://api.stability.ai")


def convert():
    global output_converted
    global convert_running

    if not convert_running and not taking_picture:
        print("Converting image")
        wait_message.show()
        response = requests.post(
            f"{api_host}/v1/generation/{engine_id}/image-to-image",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            files={
                "init_image": open(output, "rb")
            },
            data={
                "image_strength": slider.value/100,
                "init_image_mode": "IMAGE_STRENGTH",
                "cfg_scale": slider2.value,
                "samples": 1,
                "steps": 30,
                "text_prompts[0][text]": input_box.value,
                "text_prompts[0][weight]": 1,
                "text_prompts[1][text]": negative_input_box.value,
                "text_prompts[1][weight]": -1,
            }
        )

        if response.status_code != 200:
            raise Exception("Non-200 response: " + str(response.text))

        data = response.json()
        output_converted = strftime("output/generated/generated_image-%y-%d-%m_%H%M.png", gmtime())
        for i, image in enumerate(data["artifacts"]):
            with open(output_converted, "wb") as f:
                f.write(base64.b64decode(image["base64"]))

        size = 500, 500
        gif_img = Image.open(output_converted)
        gif_img.thumbnail(size, Image.ANTIALIAS)
        gif_img.save(latest_converted, 'gif')

        converted_picture.value = latest_converted
        print(slider.value/100)
        wait_message.hide()
    else:
        pass

def take_picture():
    global output
    global taking_picture
    global preview_running

    taking_picture = True

    print("Taking a picture")
    picam2.stop_preview()
    picam2.stop()
    preview_running =False
    output = strftime("output/original/image-%y-%d-%m_%H%M.png", gmtime())
    picam2.configure(still_config)
    picam2.start()
    picam2.capture_file(output)
    picam2.stop()
    picam2.configure(preview_config)
    picam2.start()
    picam2.stop_preview()
    size = 500, 500
    gif_img = Image.open(output)
    gif_img.thumbnail(size, Image.ANTIALIAS)
    gif_img.save(latest_photo, 'gif')

    picture_taken.value = latest_photo
    taking_picture = False

def take_new_picture():
    global preview_running
    print("initialized preview_running and it is ", preview_running)

    if taking_picture:
        print("camera is already taking a picture")
        return
    elif preview_running:
        print("preview is already running, taking a picture now")
        take_picture()
        return
    else:
        print("no preview running, starting new preview window")
        preview_running = True
        picam2.start_preview(Preview.QTGL, x=0, y=0, width=1000, height=600, transform=Transform(hflip=True))

def send_email():
    subject = "Neues AI Bild incoming"
    body = (f"Prompt: {input_box.value}, negative prompt: {negative_input_box.value}, cfg: {slider2.value}, "
            f"image strength {slider.value/100}")

    with open(output, 'rb') as f1:
        img_data1 = f1.read()

    with open(output_converted, 'rb') as f2:
        img_data2 = f2.read()

    image1 = MIMEImage(img_data1, name=os.path.basename(output))
    image2 = MIMEImage(img_data2, name=os.path.basename(output_converted))

    message = MIMEMultipart()
    message['Subject'] = subject
    message['From'] = sender_email
    message['To'] = recipient_email
    html_part = MIMEText(body)
    message.attach(html_part)
    message.attach(image1)
    message.attach(image2)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, message.as_string())
        server.quit()


convert_btn = Button(25)
take_pic_btn = Button(23)

convert_btn.when_pressed = convert
take_pic_btn.when_pressed = take_new_picture

picam2 = Picamera2()
preview_config = picam2.create_preview_configuration(transform=Transform(hflip=True))
still_config = picam2.create_still_configuration({"size": (1280,1024)}, transform=Transform(hflip=False))
picam2.configure(preview_config)
picam2.start()
sleep(2)
picam2.stop_preview()

app = App("Street2Paradise")

image_box = Box(app, width="fill", align="top")
picture_taken = Picture(image_box, latest_photo, align="left")
converted_picture = Picture(image_box, latest_converted, align="right")

message = Text(app, "Street2Paradise - Alexander Kutschera // Regina Sipos", align="bottom", size=12)
button = PushButton(app, command=send_email, text="Bilder drucken", align="bottom", height=1)

spacer = Box(app, width="fill", height=10, align="top")

prompt_box = Box(app, width="fill", align="top")
Text(prompt_box,"Positive Prompt:", align="left", width=30)
input_box = TextBox(prompt_box, text="A street with buildings and a lot of green area in a digital metacity",
                    width="fill",
                    align="left")

neg_prompt_box = Box(app, width="fill", align="top")
Text(neg_prompt_box,"Negative Prompt:" , align="left", width=30)
negative_input_box = TextBox(neg_prompt_box, text="blurry, bad, cars", width="fill", align="left")

spacer2 = Box(app, width="fill", height=10, align="top")

slider_box = Box(app, width="fill", align="top")
Text(slider_box,"Image strength:", align="left", width=30)
slider = Slider(slider_box, width=200, align="left")
slider.value = 35
Text(slider_box,"Prompt Adherence:", align="left", width=30)
slider2 = Slider(slider_box, width=200, align="left",start=2, end=15)
slider2.value = 7

spacer3 = Box(app, width="fill", height=10, align="top")

wait_message = Text(app, "Converting image - please wait", align="top", size=20, color="red", visible=False)

app.set_full_screen()
app.display()







