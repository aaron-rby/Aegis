# Project resources and research

## Final documents

| Material | Repository copy | Drive source |
|---|---|---|
| IDF-B report | [PDF](reports/Aegis-IDF-B-Final.pdf) | [Report](https://drive.google.com/file/d/1yvYR5gOLwIWfWfhaxUISs9oxn4_rV84w/view) |
| Final presentation | [PDF](reports/Aegis-Final-Presentation.pdf) | [Presentation](https://drive.google.com/file/d/1FE-dnqvpsMl3Tk4akafFHRlXBAn6cN4M/view) |
| Earlier literature review | [PDF](reports/Literature-Review.pdf) | [Literature review](https://drive.google.com/file/d/1FBKKESvkWacBbmicdYgeLHmrbilWRj6J/view) |

[Project document folder](https://drive.google.com/drive/folders/1Rs7gQRz6L4jBZ60WNHvU_y9cqgrrzC3j) · [Videos and photos](https://drive.google.com/drive/folders/1HNvcwVTa0PmXekuO8vypJGZRFo8zPRFB) · [Final demo video](https://drive.google.com/file/d/1nkyFItA0RH52xe4BkIHqJ0sR-sAcOO-Q/view) · [Team photo](https://drive.google.com/file/d/1HFAmDhpg8h_KVokNODOfs329gbYOHLaT/view)

[Non-geotagged hardware photos](https://drive.google.com/drive/folders/1ivJiaDGxNFYu2wD8AuOBaPseYsnONOAR) · [Geotagged hardware photos](https://drive.google.com/drive/folders/1RKaIwAZzHLd7LFzDTuzDzk11OEDlof4V)

The supplied final PDF is preserved unchanged. Source code was synchronized from the user's Projects/AI-Intrusion-Detection folder on 31 October 2026. Newer local code takes priority over older repository copies; missing operational references are retained as documented in [source recovery](source-recovery.md).

## Differences between the documents and current implementation

- The literature review is an early proposal discussing onboard camera ML, self-contained operation and possible additional deterrents. The implemented system uses **laptop inference** and a shared buzzer; other deterrents are not claimed as implemented.
- The final presentation's configuration comparison is explicitly hypothetical. Event-triggered capture is implemented, but a numerical energy saving has not been measured.
- The report records slot **E1+TE1**, faculty **Dr Debashish Dash**, laboratory **TRL 4**, hardware observations and historical image evaluations. Source resolves abbreviated prose: the sensor gate is **AND**, not OR; rearming is independent of buzzer completion.
- Dataset totals are dated snapshots. Newer candidate-training scripts are included without inferring that a model was trained or deployed.

## Research used in the final report

| Paper | Relevance and implementation context |
|---|---|
| Pugh, Brewer & Kvam (2015), *Sensor Fusion for Intrusion Detection Under False Alarm Constraints*. [DOI](https://doi.org/10.1109/SAS.2015.7133634) | Multiple-PIR intrusion detection motivates measuring detection and false alarms together. Aegis adds distance gating and visual person verification. |
| Ciuffreda, Casaccia & Revel (2023), *A Multi-Sensor Fusion Approach Based on PIR and Ultrasonic Sensors Installed on a Robot to Localise People in Indoor Environments*. [DOI](https://doi.org/10.3390/s23156963) | Complementary PIR/ultrasonic sensing. Aegis applies it to a fixed monitoring zone with capture and alarm feedback. |
| Patino et al. (2022), *Fusion of Heterogenous Sensor Data in Border Surveillance*. [DOI](https://doi.org/10.3390/s22197351) | Heterogeneous sensing and visual evidence. Different tasks and datasets do not establish Aegis's comparative superiority. |

Additional background papers are preserved in the earlier literature review. Their reported performance belongs to those studies, not Aegis.

## Prior-art context and SDGs

The report cites [US5473368A](https://patents.google.com/patent/US5473368A/en), [US9922514B2](https://patents.google.com/patent/US9922514B2/en) and [US20170076588A1](https://patents.google.com/patent/US20170076588A1/en). Combined sensing, AND logic and visual alarm verification are established approaches. These references provide technical context, not a legal patentability assessment.

The project aligns with **SDG 9** through embedded prototyping and research skills, and with the shared-space safety aims of **SDG 11**. Broader community-safety outcomes have not been measured.
