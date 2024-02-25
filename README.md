# Weissenstein-Info

Ruft diverse Infos rund um den Weisstenstein aus dem Web ab:
- Betriebszeiten Seilbahn
- Strassensperre

Läuft auf Python3 mit Selenium, Chromedriver und Paho MQTT.

Sendet Texte auf MQTT-Topic "weissenstein"

Einstellung via MQTT:
- Topic "weissenstein/control/delay": Intervall für Abfrage in Sekunden (Standard 4h)
- Topic "weissenstein/control/onoff": "stop" zum Anhalten (kein Start oder Neustart möglich)
