# Why it's built this way

## The problem

Recall studies need fixed numbers of people in each genotype and age group, with a comparison group matched on age. When the pool is thin in one group, or a criterion changes late, a hand-built list can come out unbalanced without anyone noticing.

## Design choices

**Why match men to the women who were selected rather than to the plan?** Because the plan is not the study. If the peri-menopausal stage fills only 27 of 40 places, matching men to the planned 40 would skew the comparison group towards an age band that is under-represented among the women.

**Why the largest-remainder method for splitting the male target?** Because rounding each band on its own can add up to one more or one fewer person than the target. Largest remainder always sums exactly, and breaking ties by band name means a rerun gives the same answer.

**Why deterministic selection, with an optional seed?** Because a recall list may have to be regenerated or audited months later, and the same inputs must give the same list. File order is reproducible but can carry hidden structure (IDs often follow recruitment date or site); a recorded seed gives a reproducible random draw without that bias.

**Why normalise genotypes before matching?** Because `e4/e3`, `E3E4` and `E3/E4` are one genotype written three ways. Exact string matching would silently drop people from the pool.

**Why treat e2/e4 as a switch rather than always excluding it?** Because whether an e2/e4 person counts as an "e4 carrier" is a study decision. The code makes that decision visible (`exclude_e2`) and tests both settings; e2/e2 and e2/e3 are never targets because they are neither e4 carriers nor e3/e3 controls.

**Why store shortfalls on the result instead of logging a warning?** Because warnings disappear and data does not. Anyone reading the summary file sees "7/20" next to a stage.

**Why only the standard library?** Because tools like this often run inside locked-down analysis environments where installing packages is slow or not allowed.

## Questions worth asking

**"Is age band a reasonable proxy for menopausal stage?"**
Only roughly. Age predicts stage at population level but varies a lot between individuals. The code calls the stages by age band and says so; if the study needs true staging, it has to come from questionnaire or clinical data, and the stage mapping would then be a column in the input rather than a lookup from age band.

**"What stops the same person appearing twice?"**
Within one run, each input row is used at most once because selection slices non-overlapping pools. If the input file itself has duplicate participant IDs, the tool does not detect them; that check belongs in the data preparation step (the `merge` command reports unmatched records but not duplicates). Adding a duplicate-ID check is a cheap next step.

**"How would you know the selection is not biased?"**
Compare the selected groups with the eligible pool on the variables you care about (age within band, site, recruitment date) and report the differences. The tool helps by keeping selection reproducible and by reporting shortfalls, but it does not run that comparison. With `--seed`, the draw is random within each pool, which removes the most obvious source of bias (file order).

## What's next

- Detect duplicate participant IDs and report them before selection.
- Match men on exact age within band, not only band counts.
- Write a manifest with inputs, seed, targets and shortfalls next to the lists.
