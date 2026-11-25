/**
 * Arduino Multi-Sensor Serial Telemetry Transmitter Reference Firmware.
 * 
 * Target Microcontrollers: Arduino Uno, Nano, Mega 2560, Pro Mini, ESP32.
 * Transmits comma-separated sensor telemetry bursts over Hardware Serial (UART/USB).
 * 
 * Frame Format:
 *   temp_ambient,temp_chamber,humidity,co2,pressure,voltage,current[*CHECKSUM]\r\n
 * Example:
 *   17.69,4.23,3.65,1.96,2.54,15.69,1.23*2E
 */

#define BAUD_RATE 9600
#define TRANSMIT_INTERVAL_MS 1000

// Hardware Pin Definitions (Customizable)
const int PIN_LM35_AMBIENT = A0;
const int PIN_LM35_CHAMBER = A1;
const int PIN_HUMIDITY     = A2;
const int PIN_CO2_SENSOR   = A3;
const int PIN_PRESSURE     = A4;
const int PIN_VOLTAGE_DIV  = A5;
const int PIN_ACS712_CURR  = A6;

unsigned long lastTransmitTime = 0;

void setup() {
  Serial.begin(BAUD_RATE);
  while (!Serial) {
    ; // Wait for serial port to connect (required for Leonardo/Micro)
  }
}

/**
 * Calculates 2-hex-digit XOR checksum (NMEA standard).
 */
byte calculateChecksum(const String &data) {
  byte checksum = 0;
  for (unsigned int i = 0; i < data.length(); i++) {
    checksum ^= (byte)data.charAt(i);
  }
  return checksum;
}

void loop() {
  unsigned long currentTime = millis();
  
  if (currentTime - lastTransmitTime >= TRANSMIT_INTERVAL_MS) {
    lastTransmitTime = currentTime;
    
    // 1. Acquire raw analog/digital sensor readings
    float tempAmbient = (analogRead(PIN_LM35_AMBIENT) * 500.0) / 1024.0;
    float tempChamber = (analogRead(PIN_LM35_CHAMBER) * 500.0) / 1024.0;
    float humidity    = (analogRead(PIN_HUMIDITY) * 100.0) / 1024.0;
    float co2         = (analogRead(PIN_CO2_SENSOR) * 2000.0) / 1024.0;
    float pressure    = (analogRead(PIN_PRESSURE) * 150.0) / 1024.0;
    float busVoltage  = (analogRead(PIN_VOLTAGE_DIV) * (5.0 * 5.0)) / 1024.0; // 5:1 divider
    float loadCurrent = ((analogRead(PIN_ACS712_CURR) * (5.0 / 1024.0)) - 2.5) / 0.185; // ACS712-05B

    // 2. Assemble CSV telemetry frame
    String payload = String(tempAmbient, 2) + "," +
                     String(tempChamber, 2) + "," +
                     String(humidity, 2) + "," +
                     String(co2, 2) + "," +
                     String(pressure, 2) + "," +
                     String(busVoltage, 2) + "," +
                     String(loadCurrent, 2);

    // 3. Optional XOR checksum calculation
    byte csum = calculateChecksum(payload);
    char hexChecksum[3];
    sprintf(hexChecksum, "%02X", csum);

    // 4. Transmit frame over Serial USB
    Serial.print(payload);
    Serial.print("*");
    Serial.println(hexChecksum);
  }
}
