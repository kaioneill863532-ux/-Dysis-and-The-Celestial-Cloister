import json, sys
src = sys.argv[1] if len(sys.argv) > 1 else 'out2'
t = open('ue_template.py', encoding='utf-8').read(); e = json.load(open(f'{src}/ue_expect.json'))
keys = list(e['bounds_cm'])
for a in keys:
    for b in keys:
        assert a == b or not b.endswith('_' + a), ('名字是别的名字的后缀', a, b)
open(f'{src}/ue_import_temple.py', 'w', encoding='utf-8').write(t.replace('__EXPECT__', json.dumps(e, ensure_ascii=False, separators=(',', ':'))))
print('ok', len(keys), 'meshes', len(e['probes']), 'probes')
