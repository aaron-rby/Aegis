# Results and interpretation

## Saved image evaluations

The final IDF-B report records these **person_ft.pt evaluations at threshold 0.50**. They are not measurements of the gallery worker's YOLO11m configuration at 0.35.

| Report | Person images | No-person images | TP | FN | FP | TN |
|---|---:|---:|---:|---:|---:|---:|
| Historical | 144 | 83 | 137 | 7 | 2 | 81 |
| Recovered | 136 | 82 | 129 | 7 | 2 | 80 |

TP is a person image correctly detected; FN is a person image missed; FP is a no-person image incorrectly flagged; TN is a no-person image correctly rejected. These are image classifications, not individual-person counts in multi-person scenes.

| Metric | Formula (%) | Historical calculation | Recovered result |
|---|---|---|---:|
| Precision | TP / (TP + FP) × 100 | 137 / 139 × 100 = **98.56%** | 98.47% |
| Recall | TP / (TP + FN) × 100 | 137 / 144 × 100 = **95.14%** | 94.85% |
| False-positive rate | FP / (FP + TN) × 100 | 2 / 83 × 100 = **2.41%** | 2.44% |
| Accuracy | (TP + TN) / N × 100 | 218 / 227 × 100 = **96.04%** | 95.87% |

Training/test independence remains unverified. Do not transfer these percentages to another model, dataset or physical pipeline. The report's 523 ms inference observation excludes capture, transfer, queueing and polling delay.

## Laboratory observations

The team reports laboratory validation, recorded as TRL 4 in the final report. Section 8.4 records an animal-motion scenario with no-person output and no ML alarm, and a person-presence scenario with a requested 5-second ML alarm. It lists 4–5 images and maximum reported times of 6000 ms and 5000 ms, respectively. No inference-only timing protocol is specified; these are observations, not a benchmark latency distribution.

The person trial says rearming followed clearance and buzzer completion. That describes the observed sequence; firmware rearming does not require the buzzer to finish. Prototype photos document assembly, not accuracy.

## Confidence and false alarms

The camera example's approximately 0.92 confidence is a per-detection score, not 92% system accuracy or a statistical confidence interval. No accepted box is not proof of absence. Strict filters may reject genuine small or partly visible people.

The presentation's 39.7%, 14.8% and 2.7% three-configuration false-positive rates are explicitly **hypothetical teaching figures**. A measured matched comparison has not established that reduction. Use the same labeled physical scenarios for PIR-only, dual-sensor and complete-system trials; record misses, final false alarms, preliminary beeps, invalid readings, upload failures and full latency separately.

## Dataset development

The report's 28 October snapshot records 1111 JPEG captures and 325 reviewed annotations: 166 person and 159 empty. The presentation retains an earlier 792-capture snapshot. These are dated collection counts, not accuracy measurements or current live inventory claims.

The newer local source includes optional GPU/candidate training tools. Their presence does not prove training completion or deployment. Review actual run artifacts and independent evaluations before making such claims. No candidate is deployed automatically.
