# New enhancer research resources | Recursos nuevos de enhancers

This blue-coded folder organizes the new data sources with the papers, supplementary files, and code that explain or support them. When you clone the GitHub repository, the guides, manifests, and folder skeleton are present; the larger data and publication files are downloaded with `download_project_resources.py`.

Esta carpeta azul organiza las nuevas fuentes de datos junto con los artículos, suplementos y código que las describen o respaldan. Al clonar el repositorio de GitHub, estarán disponibles las guías, los manifiestos y la estructura de carpetas; los datos y archivos de publicación se descargan con `download_project_resources.py`.

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

Use `--group all` to fetch both sets. The script verifies recorded file sizes and checksums. Oversized bundles and DNABERT model weights remain source-linked and are skipped automatically.

Desde la carpeta raíz del proyecto, ejecuta los dos comandos anteriores. Usa `--group all` para descargar ambos grupos. El programa verifica tamaños y checksums; los paquetes demasiado grandes y los pesos de DNABERT quedan enlazados a su fuente y se omiten automáticamente.

## Reading order for a computational project / Orden de lectura sugerido

1. Read the lentiMPRA paper in `02_.../PAPERS/` to understand measured sequence activity at scale.
2. Read the cross-assay paper in `03_.../PAPERS/` before combining labels; assay choice and processing can change which regions appear active.
3. Use VISTA in `04_VISTA/` as a distinct in-vivo developmental validation source.
4. Treat ENCODE cCREs as candidate annotations and compare them with functional assay labels; they are not interchangeable labels.
5. Read the hematopoiesis, DNABERT-Enhancer, and AlphaGenome guides for cell-state-specific design and computational predictions.

## Large resources not copied / Recursos grandes que no se copiaron

- The DNABERT-Enhancer trained-model archive is about 10.7 GB. Its Zenodo DOI is recorded in the study guide; the paper supplement and code snapshot are local.
- The AlphaGenome Atlas is roughly one petabyte, so its preprint and three supplementary files are local, while the Atlas itself is accessed through its official service/API.
- The earlier selective MPRA download still omits the 516 MB raw-data archive, the 25.4 GB uniform-processing archive, and the 11.1 GB reference archive. See `download_manifest.tsv` for their URLs and checksums.
