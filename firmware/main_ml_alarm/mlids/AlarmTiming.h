#pragma once
#include <stdint.h>

static constexpr uint32_t SENSOR_BEEP_MS = 1000;
static constexpr uint32_t ML_BEEP_MS = 5000;

enum class AlarmKind : uint8_t { Sensor, Ml };

struct AlarmTiming {
  bool enabled = false;
  AlarmKind kind = AlarmKind::Sensor;
  uint32_t startedAt = 0;
  uint32_t durationMs = 0;

  bool activeAt(uint32_t now) const {
    return enabled && static_cast<uint32_t>(now - startedAt) < durationMs;
  }

  bool request(uint32_t now, AlarmKind next) {
    if (activeAt(now) && kind == AlarmKind::Ml && next == AlarmKind::Sensor) return false;
    enabled = true;
    kind = next;
    startedAt = now;
    durationMs = next == AlarmKind::Ml ? ML_BEEP_MS : SENSOR_BEEP_MS;
    return true;
  }
};
