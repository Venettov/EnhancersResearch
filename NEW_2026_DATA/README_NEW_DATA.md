# Datos nuevos de enhancers — revisión del 9 de octubre de 2026

Esta carpeta separa los recursos recientes de los materiales que ya estaban en `Enhancer_Prediction/`. Conserva los datos en sus formatos originales; no se expandieron los paquetes comprimidos para evitar duplicar espacio. En Git se guardan las guías, manifiestos y scripts; los archivos grandes, artículos, suplementos y snapshots de código se reconstruyen después de clonar con `python3 NEW_2026_DATA/download_project_resources.py --group all` (Python 3.9 o superior).

## Datos descargados

| Carpeta | Contenido local |
|---|---|
| `01_ENCODE4_SCREEN/` | cCREs tipo enhancer de ENCODE, GRCh38; artículo ENCODE4 y suplementos oficiales. |
| `02_LENTIMPRA_ENCODE_2025/` | TSV, BED y BigBed procesados para ocho experimentos lentiMPRA de ENCODE; artículo, métodos, figuras y tablas suplementarias. No incluye FASTQ. |
| `03_MPRA_STARR_CROSS_ASSAY_2025/` | `lab_reported_data.tar.gz`, `output.tar.gz`, `qc.tar.gz`; artículo, suplementos y release de código. Los checksums del conjunto de datos están en el manifiesto. |
| `04_VISTA/` | 11 tablas oficiales, incluidas coordenadas hg38/mm10, experimentos, loci y diccionarios; texto completo del artículo en HTML. |
| `05_HEMATOPOIESIS_MPRA/` | `data_updated2.rda`; preprint y artículo publicado, cuatro tablas suplementarias de Cell y tres snapshots de repositorios de código. |
| `06_DNABERT_ENHANCER_2026/` | Preprint PDF, texto completo local del artículo de Bioinformatics, suplemento y snapshot del código. Los pesos del modelo están disponibles por Zenodo pero no se copiaron (10.7 GB). |
| `07_ALPHAGENOME_2026/` | Artículo principal de AlphaGenome, suplementos, preprint del Atlas y tres archivos complementarios del preprint, además del código de investigación. |

En cada carpeta numerada, `PAPERS/` guarda artículos; `SUPPLEMENTARY/`, los suplementos de la publicación; `CODE/`, snapshots del código cuando están disponibles. Consulta `STUDY_GUIDE.md` dentro de cada carpeta para saber qué leer y cómo interpretar el conjunto.

## Notas de uso

1. Conserva el tipo de ensayo y el tipo celular al comparar mediciones. Una llamada de MPRA/STARR no significa lo mismo que una anotación candidata de cCRE.
2. Verifica el ensamblaje genómico antes de cruzar BEDs o variantes; VISTA incluye coordenadas humanas y de ratón.
3. `05_HEMATOPOIESIS_MPRA/data_updated2.rda` es un archivo de R. El artículo describe qué variables procesadas usar; revisa la guía del estudio.
4. El Atlas de AlphaGenome es demasiado grande para copiarse al proyecto; usa el servicio/API oficial para consultar las variantes de interés.

## Archivos grandes disponibles en las fuentes pero no copiados

El registro MPRA/STARR incluye también `raw_data.tar.gz` (516 MB), `uniform_processed_data.tar.gz` (25.4 GB) y `reference.tar.gz` (11.1 GB); el manifiesto de datos explica sus enlaces y estados. Los pesos de DNABERT-Enhancer pesan aproximadamente 10.7 GB. El Atlas de AlphaGenome se anunció con un tamaño aproximado de 1 PB. Los artículos y suplementos descargables correspondientes sí están guardados localmente.

## Manifiestos

- `download_manifest.tsv`: datos descargados previamente, enlaces, estados, tamaños y checksums disponibles.
- `COMPANION_MATERIALS_MANIFEST.tsv`: artículos, suplementos y código guardados en esta revisión; contiene URL de origen y SHA-256.

## Fuentes principales

- ENCODE4: https://www.nature.com/articles/s41586-025-09909-9
- lentiMPRA: https://www.nature.com/articles/s41586-024-08430-9
- Evaluación MPRA/STARR-seq: https://doi.org/10.1186/s13059-025-03828-8
- VISTA: https://doi.org/10.1093/nar/gkae940
- Hematopoyesis: https://doi.org/10.1016/j.cell.2025.04.017 ; datos: https://doi.org/10.6084/m9.figshare.25713519
- DNABERT-Enhancer: https://doi.org/10.1093/bioinformatics/btag456 ; modelos: https://doi.org/10.5281/zenodo.19157566
- AlphaGenome: https://doi.org/10.1038/s41586-025-10014-0
- AlphaGenome Atlas: https://doi.org/10.64898/2026.09.16.26363192
