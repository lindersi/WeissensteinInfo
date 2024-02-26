# Abruf von Webdaten rund um den Weissenstein. Webscraping abgekupfert von StScraper.

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import datetime
import sys
import json
import paho.mqtt.client as mqtt

import secrets
import functions

mqtt_on = True
logfile = "weissenstein-info.log"  # "" = disabled

user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " \
             "Chrome/96.0.4664.45 Safari/537.36"
options = webdriver.ChromeOptions()
options.add_argument('--no-sandbox')
options.add_argument('--headless')
options.add_argument(f'user-agent={user_agent}')
options.add_argument("--window-size=1024,768")
options.add_argument('--ignore-certificate-errors')
options.add_argument('--allow-running-insecure-content')
options.add_argument("--disable-extensions")
options.add_argument("--proxy-server='direct://'")
options.add_argument("--proxy-bypass-list=*")
options.add_argument("--start-maximized")
options.add_argument('--disable-gpu')
options.add_argument('--disable-dev-shm-usage')

abrufversuche = 0
for abrufversuche in range(10):  # Anzahl Versuche im Fehlerfall

    time.sleep(abrufversuche * 60)
    abrufversuche += 1

    driver = webdriver.Chrome(options=options)

    if mqtt_on:
        # The callback for when the client receives a CONNACK response from the server.
        def on_connect(client, userdata, flags, rc):
            print("MQQT connected with result code " + str(rc))

            # Subscribing in on_connect() means that if we lose the connection and
            # reconnect then subscriptions will be renewed.
            client.subscribe("weissenstein/control/#")

        # The callback for when a PUBLISH message is received from the server.
        def on_message(client, userdata, msg):
            received = str(msg.payload.decode("utf-8"))
            if msg.topic == "weissenstein/control/onoff":
                 control['onoff'] = received
            if msg.topic == "weissenstein/control/delay":
                 control['delay'] = received
            print(msg.topic + " " + received)

        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        client.username_pw_set(secrets.mqtt_user, password=secrets.mqtt_pwd)

        client.connect(secrets.mqtt_host, secrets.mqtt_port, 60)

        # Blocking call that processes network traffic, dispatches callbacks and
        # handles reconnecting.
        # Other loop*() functions are available that give a threaded interface and a
        # manual interface.
        client.loop_start()
    # End mqtt init

    control = {
        'onoff': '',
        'delay': 4*60*60  # Sekunden (Intervall Datenabruf)
    }

    info = {}

    x = 0
    while control['onoff'] != "stop":  # Endlosschleife mit "while True" oder begrenzt mit "while x in range(n)>" oder gesteuert mit "while control['onoff'] != "stop""
        if x > 0:
            time.sleep(int(control['delay']))
        elif mqtt_on:
            client.publish('weissenstein/status', payload='Abfrage Weissenstein-Info gestartet')

        x += 1

        last_info = info  # Initiieren für späteren check, ob upgedated
        changed = True  # Beginnen mit True - wird später False, wenn sich nichts geändert hat

        try:
            # Seilbahn Weissenstein
            driver.get('https://seilbahn-weissenstein.ch/')
            element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.header-navigation'))
            )
            seilbahninfo = driver.find_elements(By.CSS_SELECTOR, 'div#article-293 div.centered-wrapper-inner p')
            for i in seilbahninfo:
                info[f'seilbahn{seilbahninfo.index(i)}'] = i.text

        except:
            print(f'Fehler beim Abruf der Seilbahn-Informationen (Versuch {abrufversuche}): ', sys.exc_info())
            if mqtt_on:
                client.publish('weissenstein/status',
                               payload=f'Fehler beim Abruf der Seilbahn-Infos (Versuch {abrufversuche}): {sys.exc_info()}')

        try:
            # Hinterweissenstein Strassensperre
            driver.get('https://www.welschenrohr.ch/neuigkeiten/verkehrsinfo-bergstrassenoev/')
            time.sleep(0)
            strasseninfo = driver.find_elements(By.CSS_SELECTOR, '.plf-text-wrapper .contenttable~.contenttable tr')
            for i in strasseninfo:
                info[f'strasse{strasseninfo.index(i)}'] = i.text

        except:
            print(f'Fehler beim Abruf der Strassen-Informationen (Versuch {abrufversuche}): ', sys.exc_info())
            if mqtt_on:
                client.publish('weissenstein/status',
                               payload=f'Fehler beim Abruf der Strassen-Infos (Versuch {abrufversuche}): {sys.exc_info()}')

        info["timestamp"] = str(datetime.datetime.now())
        info["loop"] = x

        functions.printdata(info)
        if mqtt_on:
            client.publish('weissenstein/info', payload=json.dumps(info))

        for item in info:
            if item in last_info and item not in ['timestamp', 'loop']:
                if info[item] == last_info[item] and not changed:
                    changed = False
                else:
                    changed = True
        if changed:
            functions.writefile(logfile, info)
            print(f'Daten in {logfile} geschrieben\n')
        else:
            print(f'Daten unverändert - kein Eintrag in {logfile}')

        abrufversuche = 0  # zurücksetzen, wenn alles ordentlich läuft

    driver.close()
    if mqtt_on:
        client.loop_stop()

    break  # Damit nach ordentlichem Verlassen der inneren Schleife das Programm beendet wird

print('Abruf Weisstenstein-Info wurde beendet.')
