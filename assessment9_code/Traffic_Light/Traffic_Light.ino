// Assessment 9 - Four-way traffic-light demonstration (Arduino Uno R3)
// Order: North, East, South, West.
// Every LED needs its own 220 ohm series resistor; all cathodes go to GND.
const byte redPins[4]    = {2, 5, 8, 11};
const byte yellowPins[4] = {3, 6, 9, 12};
const byte greenPins[4]  = {4, 7, 10, 13};

const unsigned long GREEN_TIME = 5000;
const unsigned long YELLOW_TIME = 2000;
const unsigned long ALL_RED_TIME = 1000;

void allRed() {
  // Remove all movement signals before enabling the stop signals.
  for (byte i = 0; i < 4; i++) {
    digitalWrite(greenPins[i], LOW);
    digitalWrite(yellowPins[i], LOW);
  }
  for (byte i = 0; i < 4; i++) {
    digitalWrite(redPins[i], HIGH);
  }
}

void setup() {
  for (byte i = 0; i < 4; i++) {
    pinMode(redPins[i], OUTPUT);
    pinMode(yellowPins[i], OUTPUT);
    pinMode(greenPins[i], OUTPUT);
  }
  allRed();
  delay(ALL_RED_TIME);
}

void loop() {
  for (byte direction = 0; direction < 4; direction++) {
    // Only this approach gets green; the other three stay red.
    digitalWrite(redPins[direction], LOW);
    digitalWrite(greenPins[direction], HIGH);
    delay(GREEN_TIME);

    digitalWrite(greenPins[direction], LOW);
    digitalWrite(yellowPins[direction], HIGH);
    delay(YELLOW_TIME);

    // Allow a clearance interval before releasing the next approach.
    allRed();
    delay(ALL_RED_TIME);
  }
}
