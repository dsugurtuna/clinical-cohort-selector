"""Generate the synthetic example files in this folder.

Every value is random. The genotype mix is an illustrative round-number
choice, not an estimate for any real population or cohort.

    python examples/make_synthetic.py
"""

import random
from pathlib import Path

HERE = Path(__file__).parent
GENOTYPES = ["E3/E3", "E3/E4", "E2/E3", "E4/E4", "E2/E4", "E2/E2"]
WEIGHTS = [60, 23, 12, 2, 2, 1]
BANDS = ["35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69"]


def main() -> None:
    rng = random.Random(2026)
    rows = ["participant_id,genotype,gender,age_band"]
    for i in range(1, 801):
        genotype = rng.choices(GENOTYPES, WEIGHTS)[0]
        gender = rng.choice(["Female", "Male"])
        rows.append(f"SYN{i:04d},{genotype},{gender},{rng.choice(BANDS)}")
    (HERE / "candidates.csv").write_text("\n".join(rows) + "\n")

    geno = [
        f"S{i:03d},SYN{i:04d},{rng.choices(GENOTYPES, WEIGHTS)[0]}"
        for i in range(1, 11)
    ]
    (HERE / "genotypes.csv").write_text("\n".join(geno) + "\n")
    pheno = [
        f"S{i:03d} {rng.randint(35, 69)} {rng.choice(['Female', 'Male'])}"
        for i in range(3, 13)
    ]
    (HERE / "phenotypes.txt").write_text("\n".join(pheno) + "\n")


if __name__ == "__main__":
    main()
