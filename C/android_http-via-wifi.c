#include <SoftwareSerial.h>
SoftwareSerial ESPserial(2, 3); // RX | TX

String content = "";
char character;

void wificmd(String cmd) {
	ESPserial.println("AT+"+cmd);
}

void resetWifi() {
	wificmd("RST");
}

void connectWifi() {
	wificmd("CWMODE=1");
	delay(1000);
	wificmd("CWJAP=\"SSID\",\"PASSWD\"");
}

void httpGet () {
	wificmd("CIPSTART=\"TCP\",\"example.com\",80");//start a TCP connection.
	if( ESPserial.find("OK")) {
		Serial.println("TCP connection ready");
	}
	delay(1000);
	String getRequest = "GET / HTTP/1.0\r\n" \
						"Host: example.com\r\n" \
						"Accept: */*\r\n" \
						"\r\n";
	// + data;
	//"Content-Length: " + data.length() + "\r\n" +
	//"Content-Type: application/x-www-form-urlencoded\r\n" +
	
	ESPserial.print("AT+CIPSEND=");
	ESPserial.println(getRequest.length());
	delay(500);

	if(ESPserial.find(">")) {
		Serial.println("Sending..");
		ESPserial.print(getRequest);

		if( ESPserial.find("SEND OK")) {
			Serial.println("Packet sent");
			while (ESPserial.available()) {
				String tmpResp = ESPserial.readString();
				Serial.println(tmpResp);
			}
			// close the connection
			wificmd("CIPCLOSE");
		}
	}
}
 
void setup() 
{
    Serial.begin(115200);
    //while (!Serial)   { ; }
 
    ESPserial.begin(115200);
 
	resetWifi();
	connectWifi();
	
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

	if(getSerialData()) {
		if (content.startsWith("get")) {
			httpGet();
		} else {
			Serial.print("ToWifi: " + content);
			ESPserial.print(content);
		}
	}
			
	if(getWifiData()) {
		Serial.print(content);
	}
}
