#!/bin/bash
#
# Portfolio/Educational Purpose Only
# -----------------------------------------------------------------------------
# This script is part of a bioinformatics portfolio demonstrating technical
# competencies in clinical cohort stratification and recall management.
#
# It contains sanitized code derived from production workflows. All internal
# paths, keys, and proprietary data have been removed or replaced with
# generic placeholders.
#
# Disclaimer: This code is for demonstration purposes and is not intended
# for clinical use without validation.
# -----------------------------------------------------------------------------
#
# Script: impact_analysis_exclusion.sh
# Description: Performs a diagnostic impact analysis to quantify how new
#              exclusion criteria (e.g., APOE-e2 carriers) affect the
#              available participant pool for a clinical study.
#

# --- Configuration ---
MASTER_FILE="./data/processed/master_participant_data.csv"
OUTPUT_DIR="./data/reports"

echo "--- Diagnostic Check: Exclusion Impact Analysis ---"

# Simulation: Create dummy master file if missing
mkdir -p "$(dirname "${MASTER_FILE}")" "${OUTPUT_DIR}"
if [ ! -f "${MASTER_FILE}" ]; then
    echo "participant_id,genotype,gender,age_band" > "${MASTER_FILE}"
    echo "P001,E3/E3,Female,40-44" >> "${MASTER_FILE}"
    echo "P002,E2/E3,Male,50-54" >> "${MASTER_FILE}" # Should be excluded
    echo "P003,E4/E4,Female,60-64" >> "${MASTER_FILE}"
fi

# Check if master file exists
if [ ! -f "$MASTER_FILE" ]; then
    echo "ERROR: Master file not found: ${MASTER_FILE}"
    exit 1
fi

# Count total participants (subtract 1 for header)
TOTAL_PARTICIPANTS=$(($(wc -l < "$MASTER_FILE") - 1))

# Count participants with an E2 allele to be excluded
E2_PARTICIPANTS=$(grep -c 'E2' "$MASTER_FILE")

# Calculate remaining participants
REMAINING_PARTICIPANTS=$((TOTAL_PARTICIPANTS - E2_PARTICIPANTS))

# Create a temporary file without E2 participants for further analysis
grep -v 'E2' "$MASTER_FILE" > "${OUTPUT_DIR}/temp_master_no_e2.csv"

# Count eligible candidates from the remaining pool
# Criteria: Female (35-69), Male (All ages)
ELIGIBLE_FEMALES=$(awk -F, 'NR>1 && $3=="Female" && $4 ~ /^(35-39|40-44|45-49|50-54|55-59|60-64|65-69)$/' "${OUTPUT_DIR}/temp_master_no_e2.csv" | wc -l)
ELIGIBLE_MALES=$(awk -F, 'NR>1 && $3=="Male"' "${OUTPUT_DIR}/temp_master_no_e2.csv" | wc -l)

# --- Summary Report ---
echo ""
echo "Total participants in master file: $TOTAL_PARTICIPANTS"
echo "Participants to be excluded (APOEe2+): $E2_PARTICIPANTS"
echo "--------------------------------------------------"
echo "Remaining participants in pool: $REMAINING_PARTICIPANTS"
echo ""
echo "Eligible candidates from the remaining pool:"
echo "  - Females (35-69): $ELIGIBLE_FEMALES"
echo "  - Males (all ages): $ELIGIBLE_MALES"
echo ""

# Cleanup temporary file
rm "${OUTPUT_DIR}/temp_master_no_e2.csv"
