# Source recovery and precedence

Newer files from the local Projects/AI-Intrusion-Detection folder take priority. Existing repository files were retained where no local replacement exists. Local reports and hardware configuration were not overwritten.

## Missing files recovered from the repository

No tracked operational file was missing from the supplied local source at review time.

Main-controller and camera source references were absent from the previous GitHub commit because the local versions embedded credentials. Sanitized versions are now included with config.example.h templates and ignored config.h files.

The separate HQ camera sketch needs its configuration template; it remains a candidate, not a replacement for the demonstrated uploader. Generated environments, captures, private annotations, weights and databases were not recovered into Git. Unrelated assessment artifacts, generated previews, obsolete phase notes and the duplicate legacy hardware-monitor workspace were subsequently removed during repository cleanup. Current runtime source, tests, final project PDFs and model provenance remain.
