"""Extract literal notebook search calls without running any Optuna objective."""
import ast
import json
from common import HERE, sha256, verify_snapshot, write_json


def recover():
    source=HERE/'vendor/DNA-Enhancers'
    verify_snapshot(source)
    path=source/'Models_Training.ipynb'
    notebook=json.loads(path.read_text())
    result={'notebook_sha256':sha256(path),'indexing':'zero-based notebook cells',
            'status':'Search specifications, not recovered best-trial outputs','models':{}}
    for name,cell in {'RF':14,'ET':21,'CB':26,'XGB':34,'LGBM':40}.items():
        tree=ast.parse(''.join(notebook['cells'][cell]['source']))
        calls=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr.startswith('suggest_'):
                calls.append({'method':node.func.attr,'args':[ast.literal_eval(x) for x in node.args],
                              'kwargs':{k.arg:ast.literal_eval(k.value) for k in node.keywords}})
        result['models'][name]={'cell':cell,'search_calls':calls}
    result['models']['MLP']={'cell':49,'search_calls':[],
        'fixed_notebook_parameters':{'solver':'adam','activation':'logistic','alpha':0.01,'hidden_layer_sizes':[20],'random_state':1}}
    result['repairs_needed_for_retuning']=[
        'Trim leading whitespace in the ET min_samples_split key.',
        'Map obsolete RF/ET max_features=auto to sqrt for classifier compatibility; deduplicate the resulting choices.',
        'Fit all suggested RF parameters, including criterion and max_leaf_nodes.',
        'Replace deprecated suggest_uniform with suggest_float preserving bounds.',
        'RF, ET, XGB and LGBM fold loops require proper aggregation; do not reuse the last split only.',
        'Choose and freeze notebook versus supplement search specifications; they differ. No retuned search has been run.'
    ]
    return result


if __name__=='__main__':
    write_json(HERE/'notebook_search_spaces.json',recover())
