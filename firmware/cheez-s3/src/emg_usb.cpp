// Batch A capture for surface EMG: one 2 s window of the Cheez sEMG-D analog output
// sampled at 1 kHz, with the module's wear-detect line read on the same clock.
//
// The module is already a finished analog front end -- gain ~1300, band-limited,
// output 0-3.3 V sitting near 1.65 V -- so nothing here filters, rectifies or
// envelopes. Raw counts are what let the host change its mind about the envelope
// after the takes are recorded, and it will: the window that works for a fist is not
// the window that works for a flick.
//
// What this firmware does owe the host is the one fact a CRC cannot carry. An
// electrode that peeled off at 0.8 s still produces 2000 perfectly checksummed
// samples of a flat line, and that take looks exactly like "relaxed" to every
// feature downstream. Only the L pin can tell the two apart, so every take reports
// what fraction of it was actually worn and the host drops the ones that were not.
//
// Probe before recording (`p`). The vendor sheet gives the L pin's levels but not
// which one means worn, and electrode position is decided by watching the number
// move, not by guessing.
//
//   ?  banner
//   p  toggle the 1 Hz live meter (baseline / swing / worn)
//   r  record one 2 s take: "EMG <hz> <n> <crc> <worn/1000> <max_gap_us> <late> <t0_ms> <arm_us>"
//      then n int16 LE. t0_ms is millis() at sample 0. arm_us is micros from the command
//      mark (before RECORDING is printed) to that same sample.
//   R  same verified take, plus best-effort S preview during capture
//   u  reboot to UF2
#include <Arduino.h>
#ifndef ARDUINO_ARCH_ESP32
#include <Adafruit_TinyUSB.h>
#endif

// S (white) -> analog in; L (yellow) -> any digital. Build flags, not constants: which
// pins are free depends on what else is on the board, and the carrier already owns D0.
#ifndef MAKO_EMG_PIN
#define MAKO_EMG_PIN A0
#endif
#ifndef MAKO_EMG_WEAR_PIN
#define MAKO_EMG_WEAR_PIN D3
#endif

constexpr uint32_t EMG_HZ = 1000, SECONDS = 2;
constexpr uint32_t EMG_COUNT = EMG_HZ * SECONDS;   // 2000 samples, 4000 bytes
// Default internal reference: 3.6 V full scale at 12 bits, same as carrier_bringup.cpp.
// The module's 3.3 V ceiling lands at count 3755, so the front end always rails before
// the ADC does -- clipping in the data is the module's, which is the one worth seeing.
constexpr long FULL_SCALE_MV = 3600;

#ifdef ARDUINO_ARCH_ESP32
// ESP32-S3 bench rig (env emg_usb_s3). Its ADC reads 0-~3.1 V at 12 dB and is not linear,
// so read calibrated millivolts and re-express them in the XIAO's 3.6 V/12-bit counts:
// usb_emg.py then converts both boards the same way.
// ponytail: tops out near 3.1 V, so module clipping above that shows as a flat top the
// host's 3.25 V rail check misses; lower RAIL_HIGH for this board if hard takes clip.
#define READ_EMG() int(analogReadMilliVolts(MAKO_EMG_PIN) * 4096L / FULL_SCALE_MV)
#define LED_STATE_ON HIGH
#else
#define READ_EMG() analogRead(MAKO_EMG_PIN)
#endif

int16_t emg[EMG_COUNT];
bool probing = false;
uint32_t probed = 0;

uint32_t crc32(const uint8_t* data, size_t size) {
  uint32_t crc = ~0u;
  while (size--) {
    crc ^= *data++;
    for (unsigned i = 0; i < 8; ++i) crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1)));
  }
  return ~crc;
}

void send(const uint8_t* data, size_t bytes) {
  size_t sent = 0;
  const uint32_t deadline = millis();
  while (Serial && sent < bytes && millis() - deadline < 20000) {
    const size_t remaining = bytes - sent;
    sent += Serial.write(data + sent, remaining < 512 ? remaining : 512);
    yield();
  }
}

// Paced sampling into emg[]. analogRead is ~10 us on the SAADC, so ~99% of every
// period is spent in yield() and FreeRTOS keeps the CDC link alive underneath.
// Returns samples taken; anything short of EMG_COUNT means the host went away and the
// take must not be sent.
uint32_t maxGapUs = 0, lateCount = 0;   // what the last capture measured about its own pacing
uint32_t captureT0Ms = 0, captureArmUs = 0;
uint32_t capture(uint32_t* wornPermille, bool preview, uint32_t markUs) {
  const uint32_t period = 1000000u / EMG_HZ;
  uint32_t worn = 0, taken = 0, next = micros(), last = 0;
  maxGapUs = 0; lateCount = 0;
  uint32_t chunkWorn = 0;
  for (uint32_t i = 0; i < EMG_COUNT; ++i) {
    while (int32_t(micros() - next) < 0) yield();
    if (int32_t(micros() - next) > int32_t(period)) ++lateCount;   // yield() came back a whole period late
    next += period;
    const uint32_t now = micros();
    if (i == 0) { captureT0Ms = millis(); captureArmUs = now - markUs; }
    if (i && now - last > maxGapUs) maxGapUs = now - last;
    last = now;
    emg[i] = int16_t(READ_EMG());
    const bool contact = digitalRead(MAKO_EMG_WEAR_PIN) == HIGH;
    worn += contact; chunkWorn += contact;
    ++taken;
    if (preview && taken % 10 == 0) {
      char line[96];
      int n = snprintf(line, sizeof(line), "S %lu %lu", (unsigned long)millis(), (unsigned long)chunkWorn);
      for (uint32_t j = taken - 10; j < taken; ++j)
        n += snprintf(line + n, sizeof(line) - n, " %d", int(emg[j]));
      line[n++] = '\n';
      // Preview is best effort; never block sampling on a slow/disconnected host.
      if (Serial.availableForWrite() >= n) Serial.write((const uint8_t*)line, n);
      chunkWorn = 0;
    }
    if (!Serial) break;
  }
  *wornPermille = taken ? (worn * 1000u) / taken : 0;
  return taken;
}

// One second of the same sampling, reduced to what a human needs while moving an
// electrode: where the baseline sits, how far the signal swings, whether L follows
// the strap. Mean and span, not RMS -- a drifting baseline is the common failure and
// RMS hides it.
void probe() {
  const uint32_t period = 1000000u / EMG_HZ;
  uint32_t worn = 0, next = micros();
  long sum = 0;
  int low = 4095, high = 0;
  for (uint32_t i = 0; i < EMG_HZ; ++i) {
    while (int32_t(micros() - next) < 0) yield();
    next += period;
    const int raw = READ_EMG();
    sum += raw;
    if (raw < low) low = raw;
    if (raw > high) high = raw;
    worn += digitalRead(MAKO_EMG_WEAR_PIN) == HIGH;
  }
  const long mean = sum / long(EMG_HZ);
  Serial.printf("emg mean=%4ldmv span=%4ldmv low=%4ldmv high=%4ldmv worn=%3lu%%\n",
                mean * FULL_SCALE_MV / 4096,
                long(high - low) * FULL_SCALE_MV / 4096,
                long(low) * FULL_SCALE_MV / 4096,
                long(high) * FULL_SCALE_MV / 4096,
                (unsigned long)(worn / 10));
}

// Live stream for the browser demo (emg_demo.html): ten paced 1 kHz samples per text line,
// "S <millis> <worn_of_10> v0..v9". Text, not the record path's binary, so a serial monitor
// can read it and a dropped byte costs one line, not the framing.
bool streaming = false;
uint32_t streamNext = 0;
void streamChunk() {
  const uint32_t period = 1000000u / EMG_HZ;
  int raw[10]; uint32_t worn = 0;
  if (streamNext == 0) streamNext = micros();
  for (int i = 0; i < 10; ++i) {
    while (int32_t(micros() - streamNext) < 0) {}
    streamNext += period;
    raw[i] = READ_EMG();
    worn += digitalRead(MAKO_EMG_WEAR_PIN) == HIGH;
  }
  Serial.printf("S %lu %lu", (unsigned long)millis(), (unsigned long)worn);
  for (int i = 0; i < 10; ++i) { Serial.print(' '); Serial.print(raw[i]); }
  Serial.println();
}

void setup() {
  Serial.begin(115200);
  pinMode(MAKO_EMG_WEAR_PIN, INPUT);
  analogReadResolution(12);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, !LED_STATE_ON);
}

void loop() {
  if (Serial.available()) {
    const char command = Serial.read();
    if (command == '?')
      Serial.printf("MAKO DAILY 1.usb-emg; USB-EMG-1; r=%lus@%luHz p=probe s=stream R=preview-record V=stream-record u=uf2\n",
                    (unsigned long)SECONDS, (unsigned long)EMG_HZ);
    if (command == 'p') { probing = !probing; probed = 0; streaming = false; }
    if (command == 's') { streaming = !streaming; probing = false; streamNext = 0; }
#ifndef ARDUINO_ARCH_ESP32
    if (command == 'u') { Serial.println("OK UF2"); Serial.flush(); delay(50); enterUf2Dfu(); }
#endif
    if (command == 'r' || command == 'R' || command == 'V') {
      probing = false; streaming = false;
      const uint32_t markUs = micros();
      Serial.printf("RECORDING %lu\n", (unsigned long)SECONDS);
      digitalWrite(LED_BUILTIN, LED_STATE_ON);
      uint32_t worn = 0;
      const uint32_t taken = capture(&worn, command != 'r', markUs);
      digitalWrite(LED_BUILTIN, !LED_STATE_ON);
      if (taken != EMG_COUNT) { Serial.println("ERROR incomplete capture"); return; }
      const uint8_t* bytes = reinterpret_cast<const uint8_t*>(emg);
      const size_t size = EMG_COUNT * 2;
      Serial.print(command == 'V' ? "EMGP " : "EMG "); Serial.print(EMG_HZ); Serial.print(' ');
      Serial.print(EMG_COUNT); Serial.print(' '); Serial.print(crc32(bytes, size), HEX);
      Serial.print(' '); Serial.print(worn); Serial.print(' '); Serial.print(maxGapUs);
      Serial.print(' '); Serial.print(lateCount); Serial.print(' '); Serial.print(captureT0Ms);
      Serial.print(' '); Serial.println(captureArmUs);
      if (command != 'V') send(bytes, size);
    }
  }
  if (probing && Serial && millis() - probed > 1000) { probed = millis(); probe(); }
  if (streaming && Serial) streamChunk(); else delay(1);
}
