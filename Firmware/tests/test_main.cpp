#include <iostream>
#include <map>
#include <assert.h>
#include "mock_arduino.h"

// Include Sources directly for simple linking in single-file test
#include "../Arduino_Motor_Controller/DCDriver.cpp"
#include "../Arduino_Motor_Controller/StepperDriver.cpp"
#include "../Arduino_Motor_Controller/ShredderController.cpp"

// Define global mock variables
std::map<int, int> pinStates;
std::map<int, int> pinModes;
std::map<int, int> analogInputs;
unsigned long mock_millis = 0;
SerialMock Serial;

void test_dc_motor_jam_detection() {
    std::cout << "Running DC Motor Jam Detection Test..." << std::endl;

    // Setup
    mock_millis = 0;
    analogInputs.clear();
    pinStates.clear();

    DCDriver dc(3, 4, A0); // PWM=3, Dir=4, Current=A0
    ShredderController controller(&dc);

    ShredderConfig config;
    config.forwardSpeed = 100;
    config.reverseSpeed = 50;
    config.currentLimit = 500; // Limit at 500
    config.reverseDuration = 1000;
    config.useImpactMode = false;

    controller.setConfig(config);
    controller.start();

    // 1. Verify Normal Run
    controller.update();
    assert(controller.getState() == STATE_FORWARD);
    assert(pinStates[3] > 0); // PWM should be active

    // 1a. Verify Inrush Masking
    // We are at time 0. Jam check starts after 500ms.
    analogInputs[A0] = 600; // Spike!
    controller.update();
    assert(controller.getState() == STATE_FORWARD); // Should IGNORE spike

    // 2. Simulate Jam (After mask time)
    mock_millis += 600; // Advance past 500ms
    controller.update();
    assert(controller.getState() == STATE_JAM_DETECTED);
    assert(pinStates[3] == 0); // Should stop

    // 3. Verify Wait period
    mock_millis += 400; // Less than 500ms wait
    controller.update();
    assert(controller.getState() == STATE_JAM_DETECTED);

    mock_millis += 200; // Cross 500ms threshold
    controller.update();
    assert(controller.getState() == STATE_REVERSE_CLEARING);
    // Should be reversing
    // DC Driver implementation: Negative speed -> Dir PIN Low
    assert(pinStates[4] == LOW);

    // 4. Verify Return to Forward
    mock_millis += 1100; // Cross reverse duration
    controller.update();
    assert(controller.getState() == STATE_FORWARD);
    assert(pinStates[4] == HIGH);

    std::cout << "DC Jam Test Passed!" << std::endl;
}

void test_impact_mode() {
    std::cout << "Running Impact Mode Test..." << std::endl;

    mock_millis = 0;
    analogInputs.clear();
    pinStates.clear();

    DCDriver dc(3, 4, A0);
    ShredderController controller(&dc);

    ShredderConfig config;
    config.forwardSpeed = 100;
    config.reverseSpeed = 50;
    config.currentLimit = 500;
    config.useImpactMode = true; // Enable Impact
    config.impactBackoffDuration = 1000;

    controller.setConfig(config);
    controller.start();

    // Trigger Jam
    mock_millis += 600; // Past inrush
    analogInputs[A0] = 600;
    controller.update();
    assert(controller.getState() == STATE_JAM_DETECTED);

    // Wait out pause
    mock_millis += 600;
    controller.update();

    // Should enter IMPACT_PREP_BACKOFF instead of REVERSE_CLEARING
    assert(controller.getState() == STATE_IMPACT_PREP_BACKOFF);
    assert(pinStates[4] == LOW); // Reversing

    // Wait out backoff
    mock_millis += 1100;
    controller.update();

    // Should enter STRIKE
    assert(controller.getState() == STATE_IMPACT_STRIKE);
    assert(pinStates[4] == HIGH); // Forward
    assert(pinStates[3] == 255); // Full Speed (map 100 -> 255)

    std::cout << "Impact Mode Test Passed!" << std::endl;
}

void test_max_jam_retries_and_fault_state() {
    std::cout << "Running Max Jam Retries and Fault State Test..." << std::endl;

    mock_millis = 0;
    analogInputs.clear();
    pinStates.clear();

    DCDriver dc(3, 4, A0);
    ShredderController controller(&dc);

    ShredderConfig config;
    config.forwardSpeed = 100;
    config.reverseSpeed = 50;
    config.currentLimit = 500;
    config.reverseDuration = 1000;
    config.useImpactMode = false;
    config.maxJamRetries = 2; // Fault after 2 jams

    controller.setConfig(config);
    controller.start();

    // Jam 1
    mock_millis += 600;
    analogInputs[A0] = 600;
    controller.update();
    assert(controller.getState() == STATE_JAM_DETECTED);
    assert(controller.getJamCount() == 1);
    assert(!controller.isFaulted());

    // Advance through pause (500ms) -> REVERSE_CLEARING
    mock_millis += 600;
    controller.update();
    assert(controller.getState() == STATE_REVERSE_CLEARING);

    // Complete reverse clearing (1000ms) -> back to FORWARD
    analogInputs[A0] = 200; // Reset load
    mock_millis += 1100;
    controller.update();
    assert(controller.getState() == STATE_FORWARD);

    // Jam 2
    mock_millis += 600;
    analogInputs[A0] = 600; // Second jam!
    controller.update();
    assert(controller.getState() == STATE_JAM_DETECTED);
    assert(controller.getJamCount() == 2);

    // Pause expires -> should enter STATE_FAULTED because jamCount (2) >= maxJamRetries (2)
    mock_millis += 600;
    controller.update();
    assert(controller.getState() == STATE_FAULTED);
    assert(controller.isFaulted());
    assert(pinStates[3] == 0); // Motor stopped

    // Subsequent updates stay in STATE_FAULTED
    mock_millis += 2000;
    controller.update();
    assert(controller.getState() == STATE_FAULTED);
    assert(controller.isFaulted());

    // Test fault reset
    controller.resetFault();
    assert(controller.getState() == STATE_IDLE);
    assert(!controller.isFaulted());
    assert(controller.getJamCount() == 0);

    std::cout << "Max Jam Retries and Fault State Test Passed!" << std::endl;
}

void test_stepper_driver_behavior_and_alarm() {
    std::cout << "Running Stepper Driver Behavior and Alarm Test..." << std::endl;

    mock_millis = 0;
    analogInputs.clear();
    pinStates.clear();
    pinModes.clear();

    const uint8_t pinStep = 3;
    const uint8_t pinDir = 4;
    const uint8_t pinEna = 5;
    const uint8_t pinAlarm = 6;

    StepperDriver stepper(pinStep, pinDir, pinEna, pinAlarm);
    stepper.begin();

    // Verify pin modes configured
    assert(pinModes[pinStep] == OUTPUT);
    assert(pinModes[pinDir] == OUTPUT);
    assert(pinModes[pinEna] == OUTPUT);
    assert(pinModes[pinAlarm] == INPUT_PULLUP);

    // Default state: disabled (Active Low enable pin is HIGH)
    assert(pinStates[pinEna] == HIGH);

    // Forward speed (positive)
    stepper.setSpeed(75);
    assert(pinStates[pinEna] == LOW);  // Enabled
    assert(pinStates[pinDir] == HIGH); // Forward direction

    // Reverse speed (negative)
    stepper.setSpeed(-50);
    assert(pinStates[pinEna] == LOW);
    assert(pinStates[pinDir] == LOW);  // Reverse direction

    // Test step pulse toggling in update()
    pinStates[pinStep] = LOW;
    mock_millis = 0;
    stepper.update();
    // Advance time past step interval (for 50%, interval is map(50, 1, 100, 10000, 200) ~ 5147us = ~5ms)
    mock_millis += 10;
    stepper.update();
    assert(pinStates[pinStep] == HIGH); // Toggled!

    // Stop motor
    stepper.stop();
    assert(pinStates[pinEna] == HIGH); // Disabled

    // Test Stepper Driver Alarm / Fault logic
    // Alarm pin is Active LOW (Leadshine standard with INPUT_PULLUP)
    pinStates[pinAlarm] = HIGH; // No alarm
    assert(!stepper.isFaulted());
    assert(stepper.getLoad() == 0);

    pinStates[pinAlarm] = LOW; // Alarm tripped
    assert(stepper.isFaulted());
    assert(stepper.getLoad() == 1023); // Max load when faulted

    // Test Stepper Driver integration with ShredderController
    ShredderController controller(&stepper);
    ShredderConfig config;
    config.forwardSpeed = 80;
    config.reverseSpeed = 40;
    config.currentLimit = 500;
    config.reverseDuration = 1000;
    config.useImpactMode = false;
    config.maxJamRetries = 2;

    controller.setConfig(config);
    controller.start();
    assert(controller.getState() == STATE_FORWARD);

    // After inrush mask (500ms), alarm pin LOW triggers jam
    mock_millis += 600;
    pinStates[pinAlarm] = LOW;
    controller.update();
    assert(controller.getState() == STATE_JAM_DETECTED);

    std::cout << "Stepper Driver Behavior and Alarm Test Passed!" << std::endl;
}

void test_load_dependent_speed_control_and_telemetry() {
    std::cout << "Running Load-Dependent Speed Control and Telemetry Test..." << std::endl;

    mock_millis = 0;
    analogInputs.clear();
    pinStates.clear();

    DCDriver dc(3, 4, A0);
    ShredderController controller(&dc);

    ShredderConfig config;
    config.forwardSpeed = 100;
    config.reverseSpeed = 50;
    config.currentLimit = 800;
    config.loadDerateThreshold = 400;
    config.minForwardSpeed = 30;
    config.enableLoadDependentSpeed = true;

    controller.setConfig(config);
    controller.start();

    // Past inrush masking
    mock_millis += 600;
    controller.update();
    assert(controller.getActiveSpeed() == 100);

    // Apply moderate load above threshold (e.g. 600, halfway between 400 and 800)
    analogInputs[A0] = 600;
    controller.update();
    // Derated speed: map(600, 400, 800, 100, 30) = 100 + (600-400)*(30-100)/(400) = 65
    assert(controller.getActiveSpeed() < 100);
    assert(controller.getActiveSpeed() >= 30);
    assert(controller.getState() == STATE_FORWARD);

    // High load near limit (790)
    analogInputs[A0] = 790;
    controller.update();
    assert(controller.getActiveSpeed() <= 35);
    assert(controller.getActiveSpeed() >= 30);

    // Return to low load (200)
    analogInputs[A0] = 200;
    controller.update();
    assert(controller.getActiveSpeed() == 100);

    // Verify Telemetry does not crash and prints
    controller.printTelemetry();

    std::cout << "Load-Dependent Speed Control and Telemetry Test Passed!" << std::endl;
}

int main() {
    test_dc_motor_jam_detection();
    test_impact_mode();
    test_max_jam_retries_and_fault_state();
    test_stepper_driver_behavior_and_alarm();
    test_load_dependent_speed_control_and_telemetry();
    std::cout << "All Firmware Tests Passed Successfully!" << std::endl;
    return 0;
}
