"""Package this root-level static site for Sites' supported dist asset layout.

The local site stays directly usable from its root. Only the deployment archive
uses dist/ and generated hosting metadata. Reads exclusively from a committed
checkout to prevent source/artifact drift. Does not include scripts or scratch data.
"""
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

checkout = Path(sys.argv[1]).resolve()
archive = Path(sys.argv[2]).resolve()
def git(*args):
    return subprocess.check_output(['git', '-C', str(checkout), *args])

config = json.loads(git('show', 'HEAD:.openai/hosting.json'))
config['static'] = {'directory': 'dist'}
paths = ['index.html', 'explorador.html', 'app.js', 'data.js', 'styles.css', 'grafo.html', 'grafo.css', 'grafo.js', '.nojekyll']
paths += git('ls-files', 'dados', 'vendor').decode().splitlines()
archive.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(archive, 'w:gz') as tar:
    files = {f'dist/{p}': git('show', 'HEAD:'+p) for p in paths}
    files['.openai/hosting.json'] = json.dumps(config, ensure_ascii=False).encode('utf-8')
    for name, content in files.items():
        info = tarfile.TarInfo(name)
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
with tarfile.open(archive) as tar:
    names = tar.getnames()
    assert 'dist/index.html' in names and '.openai/hosting.json' in names
    assert len(names) == len(files)
    assert not any(name.startswith(('tmp/', 'scripts/', '.git/')) for name in names)
print('Validated static deployment archive:', len(files), 'files')
