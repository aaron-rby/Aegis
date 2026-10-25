// Assessment 9 - LED fading with PWM (Arduino Uno R3)
// D9 -> 220 ohm resistor -> LED anode; LED cathode -> GND.
const byte ledPin = 9;
int brightness = 0;
int fadeAmount = 5;
const unsigned long FADE_DELAY = 30; // Milliseconds between updates.

void setup() {
  pinMode(ledPin, OUTPUT);
  analogWrite(ledPin, 0); // Start with the LED off.
}

void loop() {
  analogWrite(ledPin, brightness);
  delay(FADE_DELAY);

  // Clamp the value so analogWrite always receives 0 to 255.
  brightness = constrain(brightness + fadeAmount, 0, 255);

  // Reverse direction at full brightness and at zero brightness.
  if (brightness == 0 || brightness == 255) {
    fadeAmount = -fadeAmount;
  }
}
