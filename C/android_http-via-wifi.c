#include <SoftwareSerial.h>
SoftwareSerial ESPserial(2, 3); // RX | TX

/*
	TODO references:
	 * http://www.martyncurrey.com/arduino-esp8266/ (Mostly followed this with my own tweaks)
	 * http://www.esp8266.com/wiki/doku.php?id=getting-started-with-the-esp8266 (And used this for actual pinout ref)
	 * (good picture, missing one pinout from above) http://www.martyncurrey.com/wp-content/uploads/2015/01/Arduino-to-ESP8266.jpg
	 * http://www.elec-cafe.com/esp8266-at-command/
	 * http://www.elec-cafe.com/esp8266-esp-01-firmware-update/
	 * https://blogs.msdn.microsoft.com/abhinaba/2016/01/23/esp8266-wifi-with-arduino-uno-and-nano/
	 * http://www.martyncurrey.com/arduino-to-esp8266-serial-commincation/#comment-6712
*/

String content = "";
int state = 0;
char character;

void clearSerial() {
	Serial.flush();
}

void clearWifi() {
	ESPserial.flush();
}

bool wificmd(String cmd, String verify) {
	ESPserial.println("AT+"+cmd);
	if(verify != "") {
		if(ESPserial.find("OK")){
			return true;
		}
		return false;
	}
	return true;
}

void resetWifi() {
	wificmd("RST", "");
}

bool connectWifi() {
	wificmd("CWMODE=1","OK");
	delay(1000);
	return wificmd("CWJAP=\"SSID\",\"PASSWD\"", "OK");
}

int getState () {
	if( !wificmd("CIPSTART=\"TCP\",\"example.com\",8080", "OK")) { //start a TCP connection.
		return 0;
	}
	delay(1000);
	String getRequest = "STATE";
	
	ESPserial.print("AT+CIPSEND=");
	ESPserial.println(getRequest.length());
	delay(500);

	if(ESPserial.find(">")) {
		clearWifi();
		//Serial.println("Sending..");
		ESPserial.print(getRequest);

		if( ESPserial.find("SEND OK")) {
			//Serial.println("Packet sent");
			String tmpResp = "";
			while (ESPserial.available()) {
				tmpResp = ESPserial.readString();
			}
			// close the connection
			if(wificmd("CIPCLOSE", "OK")) {
				if (tmpResp.substring(11) == "1") {
					return 1;
				} else {
					return 0;
				}
			} else {
				Serial.println("Error closing connection");
			}
		} else {
			Serial.println("Error sending data");
		}
	}
	return 0;
}
 
void setup() 
{
    Serial.begin(115200);
    //while (!Serial)   { ; }
 
    ESPserial.begin(115200);
	
	while (1) {
		resetWifi();
		if(connectWifi()) {
			break;
		}
		delay(5000);
	}
	clearWifi();
}

bool getSerialData() {
	content = Serial.readString();
	if (content != "") {
		return true;
	} else {
		return false;
	}
}

bool getWifiData() {
	content = ESPserial.readString();
	if (content != "") {
		return true;
	} else {
		return false;
	}
}

void loop()
{
	/* DAS Serial-to-serial bridge.
	// listen for communication from the ESP8266 and then write it to the serial monitor
    if ( ESPserial.available() )   {  Serial.write( ESPserial.read() );  }
 
    // listen for user input and send it to the ESP8266
    if ( Serial.available() )       {  ESPserial.write( Serial.read() );  }
	*/
	//String content = "";
	//char character;

	/* DEBUG:
	if(getSerialData()) {
		if (content.startsWith("get")) {
			state = getState();
			if (state) {
				Serial.println("Powering on");
			} else {
				Serial.println("Powering down");
			}
		} else {
			//Serial.print("ToWifi: " + content);
			ESPserial.print(content);
		}
	}
			
	if(getWifiData()) {
		Serial.print(content);
	}
	*/
	state = getState();
	if (state) {
		Serial.println("Powering on");
	} else {
		Serial.println("Powering down");
	}
	delay(2000);
}
