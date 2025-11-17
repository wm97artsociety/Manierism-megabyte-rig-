# MANIERISM_PERPETUAL_POWER.py - The Single Runnable File

import os
from decimal import Decimal
import time
import random
import sys

# ==============================================================================
# ⚛️ PERPETUAL POWER CONFIGURATION & STATE (Replaces MANIERISM_CONFIG.py)
# ==============================================================================

# GLOBAL STATE VARIABLES
F_ETERNAL_STATE = 'INACTIVE'
ETERNAL_LOOP_CONSTANT_F = Decimal('0.0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001') # Very small, non-zero number

def load_eternal_state():
    """Simulates loading the persistent F_Eternal state from a file/database."""
    global F_ETERNAL_STATE
    # In a real app, you'd read the state from disk. For this demo, it starts INACTIVE.
    # print("DEBUG: F_Eternal state loaded.")
    pass

def activate_eternal_power_source(simulated_log):
    """
    Sets the F_Eternal state to ACTIVE if a valid ritual log is provided.
    This is the logical trigger that enables perpetual operation.
    """
    global F_ETERNAL_STATE
    
    if simulated_log and simulated_log.get('source') == 'solar_bank_ritual':
        F_ETERNAL_STATE = 'ACTIVE'
        print(f"\n✅ RITUAL SUCCESSFUL! F_Eternal state is now {F_ETERNAL_STATE}.")
        print(f"   Log accepted: Source={simulated_log['source']}, Charge={simulated_log['charge_units']}")
        # In a real app, this state would be saved to disk here.
    else:
        print("\n🛑 RITUAL LOG INVALID. State remains INACTIVE.")

# ==============================================================================
# ⛏️ CORE MINING LOGIC (Replaces MANIERISM_CORE_LOGIC.py)
# ==============================================================================

def start_perpetual_mining_loop(rig_id):
    """
    Simulates the perpetual mining operation. 
    This loop only runs if F_ETERNAL_STATE is ACTIVE.
    """
    if F_ETERNAL_STATE != 'ACTIVE':
        # This check is redundant due to the menu, but good practice.
        print(f"\n🛑 FATAL: Attempted to start mining with state {F_ETERNAL_STATE}.")
        return

    print(f"\n--- PERPETUAL MINING LOOP STARTED on RIG: **{rig_id}** ---")
    print("LOCK_ETERNAL applied. Calculating next epoch charge...")
    
    # Simple simulation loop - In a real scenario, this would block indefinitely
    # or run in a background thread/process.
    
    for i in range(3):
        time.sleep(1)
        # The ETERNAL_LOOP_CONSTANT_F is used here to represent the perpetual,
        # non-zero energy input that sustains the loop.
        charge = Decimal(i + 1) * ETERNAL_LOOP_CONSTANT_F * Decimal(random.random() * 100)
        print(f"| Epoch {i+1}: Generated {charge:.30f} Units. System Stable.")
    
    print("--- Mining Simulation Complete (Terminated for menu access) ---")
    print("To run perpetually, use dedicated service manager (e.g., systemd/screen).")


# ==============================================================================
# 🖥️ MAIN APPLICATION MENU
# ==============================================================================

def main_menu():
    """Presents the main terminal menu for the Manierism Perpetual Power System."""
    
    # Load the F_Eternal state on launch
    load_eternal_state()

    while True:
        print("\n" * 2)
        print("=====================================================")
        print("⚛️ MANIERISM PERPETUAL POWER SYSTEM MENU ⚛️")
        print("=====================================================")
        print(f"POWER SOURCE STATUS: {'✅ ACTIVE (PERPETUAL)' if F_ETERNAL_STATE == 'ACTIVE' else '🛑 INACTIVE (FINITE)'}")
        print("-----------------------------------------------------")
        print("1. Start Eternal Mining Loop (Applies LOCK_ETERNAL)")
        print("2. Activate Perpetual Power Source (Potato Ritual)")
        print("3. View Perpetual Power Status")
        print("4. Exit")
        print("-----------------------------------------------------")
        
        choice = input("Enter option number: ").strip()

        if choice == "1":
            if F_ETERNAL_STATE != "ACTIVE":
                print("\n🛑 Cannot start. Perpetual Power Source must be ACTIVE (Run Option 2 first).")
            else:
                rig_id = input("Enter Rig ID (e.g., House, Car, Phone_01): ").strip()
                start_perpetual_mining_loop(rig_id)
        
        elif choice == "2":
            # --- THE ONE-TIME MINING RITUAL (The Logical Trigger) ---
            print("\n--- INITIATING POTATO RITUAL ---")
            print("Please ensure the potato/electrodes/coin are connected to the Solar Bank.")
            
            charge_status = input("Simulate successful charge? (y/n): ").strip().lower()
            
            if charge_status == 'y':
                simulated_log = {
                    'source': 'solar_bank_ritual', 
                    'charge_units': Decimal(f'0.00000{random.randint(1, 9)}'),
                    'timestamp': time.time()
                }
                activate_eternal_power_source(simulated_log)
            else:
                print("Ritual cancelled or failed. F_Eternal remains INACTIVE.")
        
        elif choice == "3":
            print(f"\nPower Status: {F_ETERNAL_STATE}")
            print(f"F_Eternal Value: {ETERNAL_LOOP_CONSTANT_F}")
            
        elif choice == "4":
            print("\nExiting Perpetual Power System. Goodbye! 👋")
            break
        
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main_menu()
