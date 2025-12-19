/*
 * ESP32 Ultrasonic Sensor - QC Detector Trigger
 * 
 * Continuously reads HC-SR04 ultrasonic sensor and sends distance via Serial.
 * The QC Detector app will trigger capture when distance < threshold.
 * 
 * Wiring:
 * - VCC  -> 5V (or 3.3V for some modules)
 * - GND  -> GND
 * - TRIG -> GPIO 5
 * - ECHO -> GPIO 18
 * 
 * Upload this code to ESP32, then connect via USB.
 * The sensor_trigger.py module will auto-detect the ESP32.
 */

#define TRIG_PIN 5
#define ECHO_PIN 18
#define BAUD_RATE 115200

void setup() {
  Serial.begin(BAUD_RATE);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  
  // Wait for serial connection
  while (!Serial) {
    delay(10);
  }
  
  Serial.println("ESP32 Ultrasonic Sensor Ready");
}

void loop() {
  float distance = measureDistance();
  
  // Send distance value (Python will parse this)
  Serial.println(distance, 1);  // 1 decimal place
  
  delay(100);  // 10 readings per second
}

float measureDistance() {
  // Clear trigger
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  
  // Send 10us pulse
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  
  // Read echo pulse duration
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);  // 30ms timeout
  
  // Calculate distance in cm
  // Speed of sound = 343 m/s = 0.0343 cm/us
  // Distance = duration * 0.0343 / 2 (round trip)
  float distance = duration * 0.0343 / 2;
  
  // Return -1 if no echo (out of range)
  if (duration == 0) {
    return -1;
  }
  
  return distance;
}
