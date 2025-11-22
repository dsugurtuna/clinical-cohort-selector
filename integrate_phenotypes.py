#!/usr/bin/env python3
#
# Portfolio/Educational Purpose Only
# -----------------------------------------------------------------------------
# Script: integrate_phenotypes.py
# Description: Merges genotype data (APOE status) with clinical phenotype data
#              (Age, Gender) to create a master participant record.
#              Demonstrates Python data wrangling skills (dictionaries, CSV handling).
#

import csv
import os

# --- Configuration ---
DATA_DIR = "./data/processed"
APOE_FILE = os.path.join(DATA_DIR, "v3_to_apoe.csv")
PHENOTYPE_FILE = os.path.join(DATA_DIR, "phenotype_sampleid_age_gender.txt")
OUTPUT_FILE = os.path.join(DATA_DIR, "master_participant_data.csv")

print("--- Integrating Genotype and Phenotype Data ---")

# Simulation: Create dummy inputs if missing
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

if not os.path.exists(APOE_FILE):
    with open(APOE_FILE, 'w') as f:
        f.write("SAMP001,P001,E3/E3\n")
        f.write("SAMP002,P002,E3/E4\n")

if not os.path.exists(PHENOTYPE_FILE):
    with open(PHENOTYPE_FILE, 'w') as f:
        f.write("SAMP001 42 Female\n")
        f.write("SAMP002 55 Male\n")

# 1. Read APOE data into a dictionary
# Format: SampleID -> (ParticipantID, Genotype)
apoe_dict = {}
try:
    with open(APOE_FILE, 'r') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 3:
                # Key: SampleID, Value: (ParticipantID, Genotype)
                apoe_dict[parts[0]] = (parts[1], parts[2])
    print(f"Loaded {len(apoe_dict)} genotype records.")
except FileNotFoundError:
    print(f"Error: {APOE_FILE} not found.")
    exit(1)

# 2. Read Phenotype data and join with APOE
matches = []
try:
    with open(PHENOTYPE_FILE, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 3:
                sample_id = parts[0]
                age = parts[1]
                gender = parts[2]
                
                # Perform the join
                if sample_id in apoe_dict:
                    participant_id, apoe = apoe_dict[sample_id]
                    # Schema: sample_id, participant_id, apoe, age, gender
                    matches.append([sample_id, participant_id, apoe, age, gender])
    print(f"Found {len(matches)} matching records (Genotype + Phenotype).")
except FileNotFoundError:
    print(f"Error: {PHENOTYPE_FILE} not found.")
    exit(1)

# 3. Write the Master Record
with open(OUTPUT_FILE, 'w') as f:
    f.write('sample_id,participant_id,apoe,age,gender\n')
    for match in matches:
        f.write(','.join(match) + '\n')

print(f"Master dataset saved to: {OUTPUT_FILE}")
print("--- Integration Complete ---")
