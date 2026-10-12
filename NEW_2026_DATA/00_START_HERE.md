# New enhancer research resources | Recursos nuevos de enhancers

This blue-coded folder organizes the new data sources with the papers, supplementary files, and code that explain or support them. When you clone the GitHub repository, the guides, manifests, and folder skeleton are present; the larger data and publication files are downloaded with `download_project_resources.py`.

Esta carpeta azul organiza las nuevas fuentes de datos junto con los artículos, suplementos y código que las describen o respaldan. Al clonar el repositorio de GitHub, estarán disponibles las guías, los manifiestos y la estructura de carpetas; los datos y archivos de publicación se descargan con `download_project_resources.py`.

## Current local status / Estado local actual · 12 October 2026

The full recheck confirms all **109 resources, 51.07 GB**, are present locally, including the optional compressed cross-assay archives and DNABERT weights. There are 55 reference-checksum matches, 5 accepted-publication receipt matches, and 49 recorded-size matches with new local hashes. Downloaded files remain excluded from Git. The matched lentiMPRA specificity population is recovered, but the numerical scores are not. The local legacy test set has 100 enhancer sequences already in development data (50% of test positives; 25% of all test records).

La comprobación completa confirma los **109 recursos y 51.07 GB** locales, incluidos los archivos opcionales comprimidos y los pesos de DNABERT. Hay 55 coincidencias con checksums de referencia, 5 con constancias aceptadas y 49 con tamaños registrados y hashes locales nuevos. Los archivos descargados siguen excluidos de Git. Recuperamos la población de especificidad de lentiMPRA, pero no sus puntuaciones numéricas. La prueba histórica local incluye 100 secuencias de potenciadores ya presentes en desarrollo (50% de los positivos; 25% de toda la prueba).

**Known code blockers / Problemas de código conocidos:** the downloader still rejects five accepted publication copies because it does not consult their receipts; the archived DNABERT prediction launcher calls a missing Python file. El descargador aún rechaza cinco copias aceptadas porque no consulta sus constancias; el lanzador archivado de DNABERT llama a un archivo Python ausente. These workflows are not repaired by this documentation update. Esta actualización documental no repara esos procesos.

[Detailed audit / Auditoría detallada](../reports/02_workspace_audit_and_qc.md) · [Evidence / Evidencia](../reports/assets/2026-10-12_workspace_recheck.json) · [Notas en español](https://venettov.github.io/EnhancersResearch/es/notes.html#qc)

## Folder map / Mapa de carpetas

| Folder | Topic | Start with |
|---|---|---|
| `01_ENCODE4_SCREEN/` | ENCODE candidate regulatory elements (cCREs) | [Study guide](01_ENCODE4_SCREEN/STUDY_GUIDE.md) |
| `02_LENTIMPRA_ENCODE_2025/` | Large-scale lentiMPRA experiments | [Study guide](02_LENTIMPRA_ENCODE_2025/STUDY_GUIDE.md) |
| `03_MPRA_STARR_CROSS_ASSAY_2025/` | Comparison of MPRA and STARR-seq assays | [Study guide](03_MPRA_STARR_CROSS_ASSAY_2025/STUDY_GUIDE.md) |
| `04_VISTA/` | In-vivo developmental enhancer validation | [Study guide](04_VISTA/STUDY_GUIDE.md) |
| `05_HEMATOPOIESIS_MPRA/` | Synthetic enhancers across blood-cell states | [Study guide](05_HEMATOPOIESIS_MPRA/STUDY_GUIDE.md) |
| `06_DNABERT_ENHANCER_2026/` | Sequence-based enhancer prediction and variant effects | [Study guide](06_DNABERT_ENHANCER_2026/STUDY_GUIDE.md) |
| `07_ALPHAGENOME_2026/` | AlphaGenome model and Atlas preprint | [Study guide](07_ALPHAGENOME_2026/STUDY_GUIDE.md) |

Inside each study folder, `PAPERS/` contains article copies, `SUPPLEMENTARY/` contains publisher or preprint supporting files, and `CODE/` contains source snapshots where available. Some article copies are HTML because the publisher's open full text is available locally in that format; the study guide links to the journal version too.

Dentro de cada estudio, `PAPERS/` contiene copias de los artículos, `SUPPLEMENTARY/` contiene los archivos complementarios y `CODE/` guarda copias del código cuando está disponible. Algunas copias del artículo son HTML porque ese es el formato de texto completo abierto que se pudo guardar; la guía incluye también el enlace de la revista.

## Which files track the sources? / Dónde consultar las fuentes

- [`README_NEW_DATA.md`](README_NEW_DATA.md): guía breve en español para los datos descargados.
- [`download_manifest.tsv`](download_manifest.tsv): archivos de datos, origen, tamaño y checksum cuando estuvo disponible.
- [`COMPANION_MATERIALS_MANIFEST.tsv`](COMPANION_MATERIALS_MANIFEST.tsv): artículos, suplementos y código guardados localmente, con URL de origen y SHA-256.
- `RESOURCE_NOTES.md` in folders 06 and 07: notes about model resources and access.

## Download after cloning / Descargar después de clonar

From the project root, run:

```bash
python3 NEW_2026_DATA/download_project_resources.py --group data
python3 NEW_2026_DATA/download_project_resources.py --group papers
```

Use `--group all` to fetch both default sets. The optional large archives are about 47.7 GB extra; to fetch everything available through the project downloader, run `python3 NEW_2026_DATA/download_project_resources.py --group all --include-optional`. The downloader tries to resume interrupted transfers where the source supports it; otherwise, it safely restarts that file. Keep extra space available for extraction.

Usa `--group all` para descargar los dos grupos predeterminados. Los archivos grandes opcionales suman unos 47.7 GB; para descargar todo lo disponible mediante el programa del proyecto, ejecuta `python3 NEW_2026_DATA/download_project_resources.py --group all --include-optional`. El programa intenta reanudar las descargas interrumpidas cuando la fuente lo permite; si no, reinicia ese archivo de forma segura. Reserva espacio adicional para descomprimir los archivos.

## Reading order for a computational project / Orden de lectura sugerido

1. Read the lentiMPRA paper in `02_.../PAPERS/` to understand measured sequence activity at scale.
2. Read the cross-assay paper in `03_.../PAPERS/` before combining labels; assay choice and processing can change which regions appear active.
3. Use VISTA in `04_VISTA/` as a distinct in-vivo developmental validation source.
4. Treat ENCODE cCREs as candidate annotations and compare them with functional assay labels; they are not interchangeable labels.
5. Read the hematopoiesis, DNABERT-Enhancer, and AlphaGenome guides for cell-state-specific design and computational predictions.

## Large resources: local holdings and clone defaults / Recursos grandes: archivos locales y clonación

- The optional MPRA/STARR raw, uniformly processed, and reference archives plus DNABERT model weights are already present in the audited workspace. Their direct URLs, sizes and checksums are in `download_manifest.tsv`; after a fresh clone, download them with `--group optional` or `--group all --include-optional`. Ya están presentes localmente; el grupo opcional se refiere a una clonación nueva.
- The AlphaGenome Atlas is roughly one petabyte, so it is not a practical bulk download. See the [official downloads portal](https://alphagenome.google/downloads) and [API repository](https://github.com/google-deepmind/alphagenome) for access options and current terms.
- The complete project-download command retrieves about 51.1 GB in compressed files at the current manifest snapshot, before extraction. Check available disk space first.
