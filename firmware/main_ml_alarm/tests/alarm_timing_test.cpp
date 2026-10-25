#include "../mlids/AlarmTiming.h"
#include <assert.h>
#include <limits.h>
#include <stdio.h>

int main() {
  AlarmTiming alarm;
  assert(!alarm.activeAt(0));
  assert(alarm.request(100, AlarmKind::Sensor));
  assert(alarm.activeAt(1099));
  assert(!alarm.activeAt(1100));
  assert(alarm.request(2000, AlarmKind::Ml));
  assert(alarm.activeAt(6999));
  assert(!alarm.activeAt(7000));

  alarm.request(8000, AlarmKind::Sensor);
  alarm.request(8400, AlarmKind::Ml);
  assert(!alarm.request(9000, AlarmKind::Sensor));
  assert(alarm.activeAt(13399));
  assert(!alarm.activeAt(13400));

  // A new ML-positive burst receives its own five-second alarm window.
  alarm.request(15000, AlarmKind::Ml);
  alarm.request(17000, AlarmKind::Ml);
  assert(alarm.activeAt(21999));
  assert(!alarm.activeAt(22000));
  assert(alarm.request(22001, AlarmKind::Sensor));
  assert(!alarm.activeAt(23001));

  alarm.request(UINT32_MAX - 500, AlarmKind::Sensor);
  assert(alarm.activeAt(498));
  assert(!alarm.activeAt(499));
  puts("PASS: 1s sensor, 5s ML, priority, promotion, repeat ML, expiry and rollover");
}
