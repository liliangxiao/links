#!/bin/bash

# This script demonstrates how to use the 'links' CLI tool to define a simplified
# embedded vehicle control software architecture.
# It strictly models a unidirectional data flow to prevent any interpretation of
# "looped links" (architectural cyclic dependencies or data flow returning upstream).
# Data flows from Sensors -> ECU -> Actuators, and from ECU -> Communication (outwards only).

# --- Configuration ---
LINKS_TOOL="./links" # Path to the links executable
DATA_FILE="links_data.xml" # The data file used by the links tool

# --- Cleanup ---
# Remove previous data file to ensure a clean start
echo "1. Cleaning up previous data file ($DATA_FILE)..."
rm -f "$DATA_FILE"
echo "   If $DATA_FILE did not exist, this is normal and expected."

# --- Define Modules and Ports for a Vehicle Control System ---
echo -e "\n2. Defining vehicle control modules and their ports (strictly unidirectional)..."

# --- Establish Data Flow (Links) ---
echo -e "\n3. Establishing strictly unidirectional data flow (links)..."

# Sensor Data to ECU
echo "   - SensorModule -> ECU"
"$LINKS_TOOL" add "SensorModule::WheelSpeed_FL" "ECU::Input_WheelSpeed_FL"
"$LINKS_TOOL" add "SensorModule::WheelSpeed_FR" "ECU::Input_WheelSpeed_FR"
"$LINKS_TOOL" add "SensorModule::ThrottlePosition" "ECU::Input_ThrottlePosition"
"$LINKS_TOOL" add "SensorModule::BrakePressure" "ECU::Input_BrakePressure"

# ECU Commands to Actuator Module
echo "   - ECU -> ActuatorModule"
"$LINKS_TOOL" add "ECU::Output_Engine_RPM" "ActuatorModule::Set_Engine_RPM"
"$LINKS_TOOL" add "ECU::Output_Brake_Actuation" "ActuatorModule::Set_Brake_Actuation"

# ECU Status to Communication Module (strictly one-way out of ECU)
echo "   - ECU -> CommunicationModule (outwards only)"
"$LINKS_TOOL" add "ECU::Output_Vehicle_Status" "CommunicationModule::ReceiveECUStatus"
# The CommunicationModule::TransmitToBus is an output from the comm module itself, not linked back.
#
# Sensor Module: Collects data from physical sensors and outputs them.
echo "   - SensorModule"
"$LINKS_TOOL" edit "SensorModule::WheelSpeed_FL" "int16_t" "out" # Front-Left Wheel Speed
"$LINKS_TOOL" edit "SensorModule::WheelSpeed_FR" "int16_t" "out" # Front-Right Wheel Speed
"$LINKS_TOOL" edit "SensorModule::ThrottlePosition" "uint8_t" "out" # Accelerator Pedal Position
"$LINKS_TOOL" edit "SensorModule::BrakePressure" "uint16_t" "out" # Brake System Pressure

# ECU (Engine Control Unit) Module: Central processing and decision-making.
# Receives sensor data and external commands, outputs control signals and status.
echo "   - ECU"
"$LINKS_TOOL" edit "ECU::Input_WheelSpeed_FL" "int16_t" "in"
"$LINKS_TOOL" edit "ECU::Input_WheelSpeed_FR" "int16_t" "in"
"$LINKS_TOOL" edit "ECU::Input_ThrottlePosition" "uint8_t" "in"
"$LINKS_TOOL" edit "ECU::Input_BrakePressure" "uint16_t" "in"
"$LINKS_TOOL" edit "ECU::Output_Engine_RPM" "uint16_t" "out" # Command for engine RPM
"$LINKS_TOOL" edit "ECU::Output_Brake_Actuation" "uint8_t" "out" # Command for brake actuation
"$LINKS_TOOL" edit "ECU::Output_Vehicle_Status" "CAN_Msg" "out" # Vehicle status for communication module

# Actuator Module: Receives commands and controls physical components.
echo "   - ActuatorModule"
"$LINKS_TOOL" edit "ActuatorModule::Set_Engine_RPM" "uint16_t" "in"
"$LINKS_TOOL" edit "ActuatorModule::Set_Brake_Actuation" "uint8_t" "in"

# Communication Module: ONLY receives data from ECU for external transmission. No input to ECU.
echo "   - CommunicationModule (Outwards only)"
"$LINKS_TOOL" edit "CommunicationModule::ReceiveECUStatus" "CAN_Msg" "in" # Receives status from ECU
"$LINKS_TOOL" edit "CommunicationModule::TransmitToBus" "CAN_Msg" "out"  # Transmits externally


# --- Verify Module and Port States ---
echo -e "\n4. Verifying module and port states after linking:"
"$LINKS_TOOL" list "SensorModule"
"$LINKS_TOOL" list "ECU"
"$LINKS_TOOL" list "ActuatorModule"
"$LINKS_TOOL" list "CommunicationModule"

# --- Generate Visualization ---
echo -e "\n5. Generating graph visualization..."
"$LINKS_TOOL" dot
echo "   Check './graph.svg' or './graph.png' in the '.' directory for the visualization."

echo -e "\nScript finished. You can now use the GUI (python3 ./gui.py) or re-run 'links draw' or 'links dot' to see the current state."
