#!/usr/bin/env python3
"""Render original, bilingual SVG diagrams of the checked-in reconstruction.

Standard library only. The paper's separate JPEG is extracted unchanged from
page 4 (printed page 365) of the supplied PDF; this script never modifies it.
"""
from pathlib import Path
from html import escape
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
ASSETS=ROOT/'website/assets'

def render(language):
    es=language=='es'
    tr=lambda en,sp:sp if es else en
    pieces=['''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 1600" width="1440" height="1600" role="img" aria-labelledby="sf-title sf-desc" class="software-flowchart">
<defs><marker id="sf-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#215761"/></marker><marker id="sf-no-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#64777c"/></marker></defs>
<style>.software-flowchart text{font-family:Arial,Helvetica,sans-serif;fill:#183d46}.software-flowchart .sf-title{font-size:29px;font-weight:700}.software-flowchart .sf-node-title{font-size:25px;font-weight:700}.software-flowchart .sf-code{font-family:monospace;font-size:24px;font-weight:700}.software-flowchart .sf-line{font-size:23px}.software-flowchart .sf-small{font-size:18px;fill:#526b70}.software-flowchart .sf-label{font-size:21px;font-weight:700}.software-flowchart a:hover text{text-decoration:underline}</style>''']
    def add(x):pieces.append(x)
    def text(x,y,value,css='sf-line',anchor='start'):
        add(f'<text x="{x}" y="{y}" class="{css}" text-anchor="{anchor}">{escape(value)}</text>')
    def rect(x,y,w,h,fill='#fff',stroke='#cedcd8',radius=16):
        add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    def path(d,no=False):add(f'<path d="{d}" fill="none" stroke="'+('#64777c' if no else '#215761')+'" stroke-width="3" stroke-linejoin="round" marker-end="url(#'+('sf-no-arrow' if no else 'sf-arrow')+')"/>')
    def node(key,x,y,w,h,title,lines,fill='#edf5f1',code=False,script=None):
        add(f'<g data-sf-node="{key}">');rect(x,y,w,h,fill)
        if script:add(f'<a href="https://github.com/Venettov/EnhancersResearch/blob/main/replication/ienhancer_2l/{script}" target="_blank" rel="noopener noreferrer">')
        text(x+22,y+36,title,'sf-code' if code else 'sf-node-title')
        if script:add('</a>')
        for i,line in enumerate(lines):text(x+22,y+70+29*i,line)
        add('</g>')
    add('<title id="sf-title">'+escape(tr('Our iEnhancer-2L software: data preparation, grouped evaluation, final fitting, and two-stage prediction','Nuestro software iEnhancer-2L: preparación, evaluación por grupos, ajuste final y predicción en dos etapas'))+'</title>')
    add('<desc id="sf-desc">'+escape(tr('Original sequences and S1 labels are checked. S2 properties and verified hg19 receipts yield 4105 features and 2451 related-sequence groups. Nested evaluation keeps groups together. A separate training-only search fits two final models. For a new 200-base sequence, layer I predicts enhancer or non-enhancer. Only predicted enhancers reach layer II, which predicts strong or weak. All routes produce a CSV record.','Se comprueban las secuencias originales y etiquetas S1. Las propiedades S2 y comprobaciones hg19 generan 4105 características y 2451 grupos de secuencias relacionadas. La evaluación anidada mantiene juntos los grupos. Una búsqueda separada solo con entrenamiento ajusta dos modelos finales. Para una nueva secuencia de 200 bases, la etapa I predice potenciador o no potenciador. Solo los potenciadores predichos pasan a la etapa II, que predice fuerte o débil. Todas las rutas generan un registro CSV.'))+'</desc>')
    rect(0,0,1440,1600,'#f7f7f1','#f7f7f1',0)
    rect(28,24,1384,82,'#e5f0eb')
    text(52,58,tr('Python + .venv run the code · Git/GitHub preserve inputs, code versions, and evidence','Python + .venv ejecutan el código · Git/GitHub conservan entradas, versiones y evidencia'),'sf-line')
    text(52,87,tr('VS Code is an optional editor and terminal; it does not supply the prediction method.','VS Code es un editor y terminal opcional; no proporciona el método de predicción.'),'sf-small')
    rect(28,128,1384,586)
    text(52,172,tr('1. Prepare, train, and evaluate the reconstruction','1. Preparar, entrenar y evaluar la reconstrucción'),'sf-title')
    rect(28,744,1384,790)
    text(52,788,tr('2. Apply the saved models to new DNA','2. Aplicar los modelos guardados a nuevo ADN'),'sf-title')
    # Draw connections first so node content remains unobscured.
    path('M390 263H430');path('M720 263H760')
    path('M1070 352V366H365V392');path('M1070 352V366H1055V392')
    path('M365 544V566');path('M1055 544V566')
    path('M1055 638V826')
    path('M390 891H430');path('M780 891H850')
    path('M960 956V1000H670V1038')
    path('M1230 956V1038',no=True)
    path('M670 1176V1198H425V1244');path('M670 1176V1198H915V1244')
    path('M425 1334V1370H800V1400');path('M915 1334V1370H800V1400')
    path('M1210 1150V1370H800V1400',no=True)
    node('inputs',60,198,330,130,tr('Original inputs','Entradas originales'),tr(['FASTA · 200 bases','S1 class labels'],['FASTA · 200 bases','Etiquetas de clase S1']))
    node('prepare',430,198,290,130,'prepare_data.py',tr(['Check hashes + labels','2,968 sequences'],['Hashes + etiquetas','2,968 secuencias']),code=True,script='prepare_data.py')
    node('features',760,198,620,154,'build_features.py',tr(['S2 properties + verified hg19 receipts','NumPy + RapidFuzz: 2,451 sequence groups','Fixed folds + 4,105 PseKNC features per sequence'],['Propiedades S2 + registros hg19 verificados','NumPy + RapidFuzz: 2,451 grupos de secuencias','Particiones fijas + 4,105 características PseKNC']),code=True,script='build_features.py')
    node('evaluation',60,392,610,152,'train_svm.py',tr(['Grouped evaluation · scikit-learn/LIBSVM + SciPy','5 outer folds test; 3 inner folds select settings','Related sequences stay together'],['Evaluación por grupos · scikit-learn/LIBSVM + SciPy','5 particiones externas; 3 internas eligen parámetros','Las secuencias relacionadas permanecen juntas']),code=True,script='train_svm.py')
    node('final-fit',730,392,650,152,'train_svm.py',tr(['Final fit after a training-only five-fold search','Layer I: 2,968; layer II: 1,484 known enhancers','Fit each final model on all its training records'],['Búsqueda solo con entrenamiento: 5 particiones','I: 2,968; II: 1,484 potenciadores conocidos','Ajustar cada modelo final con todo su entrenamiento']),code=True,script='train_svm.py')
    node('evaluation-output',60,566,610,72,tr('Held-out predictions → metrics + audit files','Predicciones reservadas → métricas + auditoría'),[],fill='#f1f5f7')
    node('models',730,566,650,72,tr('Two saved final models (.npz)','Dos modelos finales guardados (.npz)'),[],fill='#dceee5')
    text(60,674,tr('Historical 400-record test: diagnostic only; 100 training duplicates. Excluded from evaluation.','Prueba histórica de 400 registros: solo diagnóstico; 100 duplicados. Excluida de la evaluación.'),'sf-small')
    text(60,701,tr('No NEW_2026_DATA activity measurements are used in fitting.','El ajuste no utiliza mediciones de actividad de NEW_2026_DATA.'),'sf-small')
    text(1078,734,tr('Saved models','Modelos guardados'),'sf-small')
    node('query',60,826,330,130,tr('New query FASTA','Nueva consulta FASTA'),tr(['200 A/C/G/T bases','One record per sequence'],['200 bases A/C/G/T','Un registro por secuencia']))
    node('predict',430,826,350,130,'predict_svm.py',tr(['Same feature calculations','A feature vector for each layer'],['Mismas características','Un vector para cada etapa']),code=True,script='predict_svm.py')
    node('layer1',850,826,530,130,tr('Layer I · enhancer?','Etapa I · ¿potenciador?'),tr(['Saved RBF SVM · weight w = 0.1','Score > 0 continues to layer II'],['SVM RBF guardada · peso w = 0.1','Puntuación > 0 continúa a la etapa II']),fill='#e3f0eb')
    text(846,991,tr('Yes (> 0)','Sí (> 0)'),'sf-label')
    text(1250,999,tr('No (≤ 0)','No (≤ 0)'),'sf-label')
    node('layer2',440,1038,460,138,tr('Layer II · strength','Etapa II · fuerza'),tr(['Saved RBF SVM · weight w = 0.4','Only after a positive layer-I call'],['SVM RBF guardada · peso w = 0.4','Solo tras una etapa I positiva']),fill='#e3f0eb')
    node('non-enhancer',1060,1038,300,112,tr('Non-enhancer','No potenciador'),tr(['Skip layer II'],['Omitir la etapa II']),fill='#edf0f1')
    text(447,1228,tr('Score > 0','Puntuación > 0'),'sf-label')
    text(937,1228,tr('Score ≤ 0','Puntuación ≤ 0'),'sf-label')
    node('strong',260,1244,330,90,tr('Strong enhancer','Potenciador fuerte'),[],fill='#dceee5')
    node('weak',750,1244,330,90,tr('Weak enhancer','Potenciador débil'),[],fill='#faf0dc')
    node('csv',60,1400,1320,86,tr('Prediction CSV: final class + local decision scores','CSV de predicción: clase final + puntuaciones de decisión locales'),[],fill='#f1f5f7')
    text(60,1514,tr('Frozen labels can be compared with the authors’ server; no feedback into model tuning.','Las etiquetas fijas se comparan con el servidor de los autores, sin usarlas para reajustar modelos.'),'sf-small')
    text(48,1571,tr('Scores are not measured activity. The HepG2/K562/WTC11 activity comparison remains planned.','Las puntuaciones no son actividad medida. La comparación de actividad HepG2/K562/WTC11 sigue planificada.'),'sf-small')
    add('</svg>')
    return '\n'.join(pieces)+'\n'

def main():
    for language in ('en','es'):
        target=ASSETS/f'ienhancer-2l-software-flow-{language}.svg'
        target.write_text(render(language))
        print(target.relative_to(ROOT))

if __name__=='__main__':main()
