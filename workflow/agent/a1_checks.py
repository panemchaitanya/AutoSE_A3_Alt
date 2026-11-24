"""Mechanical minimum A1 deliverable checks. Semantic validation remains a judge duty.

Bundle selection contract (source: the A1 skill's naming rule
`<slug>_<KIND>_v<N>.md`, KIND in SRS/REGISTER/VALIDATION, N numeric):
- exactly one slug may be present; conflicting slugs are rejected;
- the selected bundle is the highest NUMERIC version (v10 > v2, never
  filename order);
- the selected version must contain all three kinds; missing matching
  pieces are rejected, components are never mixed across versions.
"""
import glob,os,re
from pathlib import Path

A1_FILE_RE = re.compile(r'^(.+)_(SRS|REGISTER|VALIDATION)_v(\d+)\.md$')
A1_KINDS = ('SRS','REGISTER','VALIDATION')

def _scan(root):
    found={}
    pattern=os.path.join(root,'.autose','artifacts','*_v*.md')
    for path in sorted(glob.glob(pattern)):
        m=A1_FILE_RE.match(os.path.basename(path))
        if not m:continue
        slug,kind,ver=m.group(1),m.group(2),int(m.group(3))
        found.setdefault(slug,{}).setdefault(ver,{})[kind]=path
    return found

def check_a1_bundle(root):
    errors=[];docs={}
    found=_scan(root)
    if not found:
        for kind in A1_KINDS:errors.append(f'missing versioned A1 {kind} artifact')
    elif len(found)>1:
        errors.append('ambiguous A1 bundle: conflicting slugs present: '
                      +', '.join(sorted(found))
                      +'; exactly one slug with one selected numeric version is required')
    else:
        slug=next(iter(found))
        selected=max(found[slug])
        bundle=found[slug][selected]
        for kind in A1_KINDS:
            if kind not in bundle:
                errors.append(f'A1 {kind} missing for selected bundle {slug} v{selected}; components are never mixed across versions')
        if all(k in bundle for k in A1_KINDS):
            for kind in A1_KINDS:
                docs[kind]=Path(bundle[kind]).read_text(encoding='utf-8')
                if len(docs[kind].strip())<160:errors.append(f'A1 {kind} artifact is too short to contain required sections')
    expected={'SRS':['purpose','actors','constraints','functional requirements','non-functional','acceptance criteria','dependencies','traceability'],
              'REGISTER':['source statements','ambiguous','open questions','assumptions','conflicts','evidence','coverage','change log'],
              'VALIDATION':['verdict','gate','basis','tool','human']}
    for kind,terms in expected.items():
        text=docs.get(kind,'').lower()
        if not text:continue
        for term in terms:
            if term not in text:errors.append(f'{kind} missing required topic: {term}')
    val=docs.get('VALIDATION','')
    required=['C1','C2','C3','C4','K1','K2','K3','R-1','R-2','R-3','F1','F2','T1','T2','T3','T4','E1','E2','E3','E4','E5']
    for key in required:
        if not re.search(r'\b'+re.escape(key)+r'\b[^\n]*(?:PASS|FAIL|N/A)',val,re.I):
            errors.append(f'VALIDATION lacks explicit PASS/FAIL/N/A result for {key}')
    if not re.search(r'\b(?:READY|PARTIALLY READY|NOT READY)\b',val):errors.append('VALIDATION lacks readiness verdict')
    if docs.get('SRS') and not re.search(r'\bS-\d+',docs['SRS']):errors.append('SRS lacks source statement links')
    return not errors,errors,docs
