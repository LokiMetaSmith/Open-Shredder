#include "ShredderController.h"

#ifdef ARDUINO
    #include <Arduino.h>
#else
    #include "../tests/mock_arduino.h"
#endif

ShredderController::ShredderController(MotorInterface* motor) {
    _motor = motor;
    _state = STATE_IDLE;
    _jamCount = 0;

    // Defaults
    _config.forwardSpeed = 100;
    _config.reverseSpeed = 50;
    _config.currentLimit = 800;
    _config.runDuration = 0;
    _config.reverseDuration = 2000;
    _config.useImpactMode = false;
    _config.impactBackoffDuration = 1000;
    _config.maxJamRetries = 3;
    _config.enableLoadDependentSpeed = false;
    _config.loadDerateThreshold = 600;
    _config.minForwardSpeed = 40;
    _activeForwardSpeed = _config.forwardSpeed;
}

void ShredderController::setConfig(ShredderConfig config) {
    _config = config;
    _activeForwardSpeed = _config.forwardSpeed;
}

void ShredderController::start() {
    _state = STATE_FORWARD;
    _stateStartTime = millis();
    _runStartTime = millis();
    _activeForwardSpeed = _config.forwardSpeed;
    _motor->setSpeed(_activeForwardSpeed);
    _jamCount = 0;
}

void ShredderController::stop() {
    _state = STATE_IDLE;
    _motor->stop();
}

void ShredderController::resetFault() {
    if (_state == STATE_FAULTED) {
        _state = STATE_IDLE;
        _jamCount = 0;
        _motor->stop();
    }
}

void ShredderController::update() {
    unsigned long now = millis();
    _motor->update(); // Tick the motor driver

    // State Machine
    switch (_state) {
        case STATE_IDLE:
            // Do nothing
            break;

        case STATE_FORWARD:
            // Check Timeout
            if (_config.runDuration > 0 && (now - _runStartTime > _config.runDuration)) {
                stop();
                return;
            }

            // Inrush Masking: Ignore current spikes during the first 500ms of entering STATE_FORWARD
            if (now - _stateStartTime > 500) {
                int currentLoad = _motor->getLoad();

                // Check Jam/Fault
                if (currentLoad > _config.currentLimit || _motor->isFaulted()) {
                    _state = STATE_JAM_DETECTED;
                    _stateStartTime = now;
                    _motor->stop();
                    _jamCount++;
                } else if (_config.enableLoadDependentSpeed && currentLoad > _config.loadDerateThreshold) {
                    // Elevated load detected: dynamically derate speed between forwardSpeed and minForwardSpeed
                    int targetSpeed = map(currentLoad, _config.loadDerateThreshold, _config.currentLimit, _config.forwardSpeed, _config.minForwardSpeed);
                    if (targetSpeed < _config.minForwardSpeed) targetSpeed = _config.minForwardSpeed;
                    if (targetSpeed > _config.forwardSpeed) targetSpeed = _config.forwardSpeed;
                    if (targetSpeed != _activeForwardSpeed) {
                        _activeForwardSpeed = targetSpeed;
                        _motor->setSpeed(_activeForwardSpeed);
                    }
                } else if (_config.enableLoadDependentSpeed && _activeForwardSpeed != _config.forwardSpeed) {
                    // Normal load restored: restore full forward speed
                    _activeForwardSpeed = _config.forwardSpeed;
                    _motor->setSpeed(_activeForwardSpeed);
                }
            }
            break;

        case STATE_JAM_DETECTED:
            // Pause briefly before reversing to protect electronics
            if (now - _stateStartTime > 500) {
                if (_config.maxJamRetries > 0 && _jamCount >= _config.maxJamRetries) {
                    // Exceeded max allowable jam retries; enter terminal fault state
                    _state = STATE_FAULTED;
                    _motor->stop();
                } else if (_config.useImpactMode) {
                    // Impact Strategy: Back up, then strike
                    _state = STATE_IMPACT_PREP_BACKOFF;
                    _motor->setSpeed(-_config.reverseSpeed);
                } else {
                    // Standard Strategy: Reverse, then Forward
                    _state = STATE_REVERSE_CLEARING;
                    _motor->setSpeed(-_config.reverseSpeed);
                }
                _stateStartTime = now;
            }
            break;

        case STATE_REVERSE_CLEARING:
            if (now - _stateStartTime > _config.reverseDuration) {
                _state = STATE_FORWARD;
                _activeForwardSpeed = _config.forwardSpeed;
                _motor->setSpeed(_activeForwardSpeed);
                _stateStartTime = now;
            }
            break;

        case STATE_IMPACT_PREP_BACKOFF:
            // Back up significantly
            if (now - _stateStartTime > _config.impactBackoffDuration) {
                _state = STATE_IMPACT_STRIKE;
                // Full speed forward for maximum inertia
                _motor->setSpeed(100);
                _stateStartTime = now;
            }
            break;

        case STATE_IMPACT_STRIKE:
            // Switch back to FORWARD after a brief acceleration period
            if (now - _stateStartTime > 500) {
                _state = STATE_FORWARD;
                _activeForwardSpeed = _config.forwardSpeed;
                _motor->setSpeed(_activeForwardSpeed);
                _stateStartTime = now;
            }
            break;

        case STATE_PAUSED:
            // Placeholder
            break;

        case STATE_FAULTED:
            // Terminal fault state - keep motor stopped until explicitly cleared
            _motor->stop();
            break;
    }
}

void ShredderController::printTelemetry() {
    Serial.print("TELEMETRY:state=");
    Serial.print(_state);
    Serial.print(",load=");
    Serial.print(_motor->getLoad());
    Serial.print(",speed=");
    Serial.print(_activeForwardSpeed);
    Serial.print(",jams=");
    Serial.print(_jamCount);
    Serial.print(",fault=");
    Serial.println(isFaulted() ? 1 : 0);
}
