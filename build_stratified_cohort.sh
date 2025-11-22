#!/usr/bin/env bash
#
# Portfolio/Educational Purpose Only
# -----------------------------------------------------------------------------
# Script: build_stratified_cohort.sh
# Description: The core logic for building a balanced clinical recall list.
#              1. Filters candidates by genotype (E3/E3, E3/E4, E4/E4).
#              2. Stratifies females into 4 age stages (Pre, Peri, Early, Late).
#              3. Builds an age-matched male cohort proportional to the females.
#              4. Generates final CSV deliverables for the clinical team.
#

set -euo pipefail
export LC_ALL=C

# --- Configuration ---
PROJECT_ROOT="$(pwd)"
DATA_DIR="./data/processed"
DELIV="./data/deliverables"
TMP="./data/tmp"
HEADER="participant_id,genotype,gender,age_band"
STAGES=("pre:35-39,40-44" "peri:45-49" "early:50-54" "late:55-59,60-64,65-69")

# --- Setup and Validation ---
mkdir -p "$DELIV" "$TMP" "$DATA_DIR"

# Simulation: Create dummy input files if missing
if [ ! -f "${DATA_DIR}/available_females_list.csv" ]; then
    echo "${HEADER}" > "${DATA_DIR}/available_females_list.csv"
    echo "F001,E3/E3,Female,40-44" >> "${DATA_DIR}/available_females_list.csv"
    echo "F002,E3/E4,Female,45-49" >> "${DATA_DIR}/available_females_list.csv"
fi
if [ ! -f "${DATA_DIR}/available_males_list.csv" ]; then
    echo "${HEADER}" > "${DATA_DIR}/available_males_list.csv"
    echo "M001,E3/E3,Male,40-44" >> "${DATA_DIR}/available_males_list.csv"
fi

req() {
  [[ -s "$1" ]] || { echo "ERROR: required file '$1' not found or empty."; exit 1; }
}
req "${DATA_DIR}/available_females_list.csv"
req "${DATA_DIR}/available_males_list.csv"

rm -f "$DELIV"/*

echo "--- Building Clean Candidate Pools (with APOEe2 exclusion) ---"
# Create filtered and sorted pools of candidates
# Logic: Exclude E2 carriers, keep only target genotypes
awk -F',' 'BEGIN{OFS=","}
  NR==1{next}
  ($2!="E3/E3" && $2!="E3/E4" && $2!="E4/E4") || $2 ~ /E2/ {next} 
  $3=="Female" && ($4=="35-39"||$4=="40-44"||$4=="45-49"||$4=="50-54"||$4=="55-59"||$4=="60-64"||$4=="65-69") {print $0}
' "${DATA_DIR}/available_females_list.csv" | sort -t',' -k1,1n > "$TMP/fem_pool.csv"

awk -F',' 'BEGIN{OFS=","}
  NR==1{next}
  ($2!="E3/E3" && $2!="E3/E4" && $2!="E4/E4") || $2 ~ /E2/ {next}
  $3=="Male" {print $0}
' "${DATA_DIR}/available_males_list.csv" | sort -t',' -k1,1n > "$TMP/male_pool.csv"

# --- Female Stage Construction ---
# Function to build a specific age stage (e.g., "Pre-Menopausal")
build_stage () {
  local stage_name="$1"; local bands_csv="$2"; local out="$DELIV/female_${stage_name}.csv"
  echo "$HEADER" > "$out"
  awk -F',' -vOFS=',' -vBANDS="$bands_csv" -vSTAGE="$stage_name" '
    BEGIN{
      nB=split(BANDS, b, ",");
      for(i=1;i<=nB;i++) keep[b[i]]=1;
    }
    {
      if(keep[$4]){
        if($2=="E3/E3"){ e33[++n33]=$0; }
        else if($2=="E3/E4"){ e34[++n34]=$0; }
        else if($2=="E4/E4"){ e44[++n44]=$0; }
      }
    }
    END{
      # Target: 80 E4+ and 80 E3/E3 per stage (Simulation targets reduced for demo)
      needed4=1; needed33=1; 
      
      c4=0;
      for(i=1;i<=n34 && c4<needed4;i++){ print e34[i]; c4++; }
      for(i=1;i<=n44 && c4<needed4;i++){ print e44[i]; c4++; }
      c33=0;
      for(i=1;i<=n33 && c33<needed33;i++){ print e33[i]; c33++; }
    }
  ' "$TMP/fem_pool.csv" >> "$out"
}

echo "--- Building 4 Female Stages ---"
for spec in "${STAGES[@]}"; do
  name="${spec%%:*}"; bands="${spec#*:}"
  build_stage "$name" "$bands"
done

# --- Combine Females into Final List ---
echo "$HEADER" > "$DELIV/female_recall_list.csv"
for s in pre peri early late; do
  tail -n +2 "$DELIV/female_${s}.csv" >> "$DELIV/female_recall_list.csv"
done

# --- Build Age-Matched Male List ---
echo "--- Calculating Male Targets and Building List ---"
# Compute per-band male targets proportionally to the females
awk -F',' -v total_e4=1 -v total_e33=1 '
  BEGIN{ tot=0; }
  NR>1 { b=$4; cnt[b]++; tot++; }
  END{
    if(tot==0){ exit 0; }
    print "age_band,e4plus,e3e3";
    for(b in cnt){
      share=cnt[b]/tot;
      e4=int(share*total_e4 + 0.9); 
      e33=int(share*total_e33 + 0.9);
      print b "," e4 "," e33;
    }
  }
' "$DELIV/female_recall_list.csv" > "$TMP/male_targets.csv"

# Build male recall list using the calculated targets
if [ -s "$TMP/male_targets.csv" ]; then
    {
      echo "$HEADER"
      awk -F',' -vOFS=',' '
        FNR==1 && NR==FNR { next }
        FNR>1 && NR==FNR { tgt_e4[$1]=$2; tgt_e33[$1]=$3; order[++n]=$1; next }
        NR>FNR {
          b=$4; g=$2;
          if(g=="E3/E4"){ e34[b, ++n34[b]]=$0; }
          else if(g=="E4/E4"){ e44[b, ++n44[b]]=$0; }
          else if(g=="E3/E3"){ e33[b, ++n33[b]]=$0; }
        }
        END{
          for(i=1;i<=n;i++){
            b=order[i];
            need4 = (b in tgt_e4 ? tgt_e4[b] : 0);
            need33 = (b in tgt_e33 ? tgt_e33[b] : 0);
            c4=0;
            for(j=1;j<=n34[b] && c4<need4;j++){ print e34[b,j]; c4++; }
            for(j=1;j<=n44[b] && c4<need4;j++){ print e44[b,j]; c4++; }
            c33=0;
            for(j=1;j<=n33[b] && c33<need33;j++){ print e33[b,j]; c33++; }
          }
        }
      ' "$TMP/male_targets.csv" "$TMP/male_pool.csv"
    } > "$DELIV/male_recall_list.csv"
else
    echo "Warning: No male targets generated (likely empty female list)."
fi

# --- Final Summary Report ---
echo "--- Generating Final Summary ---"
{
  echo "RECALL SUMMARY - $(date)"
  echo
  echo "[Female combined]"
  awk -F',' 'NR>1{ if($2=="E3/E3") e33++; else if($2=="E3/E4"||$2=="E4/E4") e4++; tot++; }
    END{ printf("  total=%d (E3/E3=%d, e4+=%d)\n", tot, e33, e4); }' \
    "$DELIV/female_recall_list.csv"
  echo
  echo "[Male recall]"
  if [ -f "$DELIV/male_recall_list.csv" ]; then
      awk -F',' 'NR>1{ if($2=="E3/E3") e33++; else if($2=="E3/E4"||$2=="E4/E4") e4++; tot++; }
        END{ printf("  total=%d (E3/E3=%d, e4+=%d)\n", tot, e33, e4); }' \
        "$DELIV/male_recall_list.csv"
  else
      echo "  total=0"
  fi
} > "$DELIV/recall_summary.txt"

# --- Tidy Up ---
rm -rf "$TMP"

echo "✔ Deliverables built in '$DELIV/'"
