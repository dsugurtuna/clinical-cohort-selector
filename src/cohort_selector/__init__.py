"""
Clinical Cohort Selector
========================

Precision medicine toolkit for stratifying patient cohorts based on
genotype, age, and gender for clinical recall studies.

Author: Ugur Tuna
"""

__version__ = "2.0.0"

from cohort_selector.stratifier import CohortStratifier
from cohort_selector.impact import ExclusionImpactAnalyser
from cohort_selector.integrator import PhenotypeIntegrator

__all__ = ["CohortStratifier", "ExclusionImpactAnalyser", "PhenotypeIntegrator"]
