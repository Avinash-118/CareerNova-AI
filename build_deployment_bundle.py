"""Create an explicit backend source bundle, without secrets or personal files."""
from pathlib import Path
import shutil
import zipfile


def build_bundle():
    root=Path(__file__).resolve().parent
    destination=root/'.deploy'/'backend'
    destination.mkdir(parents=True,exist_ok=True)
    # A dedicated generated directory; clear files only, never traverse arbitrary paths.
    for old in destination.iterdir():
        if old.is_file():old.unlink()
    files=[p for p in root.glob('*.py') if not p.name.startswith('test_')
           and not any(word in p.name for word in ('backup','before_'))
           and p.name not in {'app.py','import_jobs.py','prepare_jobs.py','build_index.py','verify_faiss.py','configure_integrations.py','build_deployment_bundle.py','configure_deployment.py'}]
    files += [root/'Dockerfile',root/'requirements.txt',root/'.dockerignore']
    for source in files:shutil.copy2(source,destination/source.name)
    (destination/'README.md').write_text('---\ntitle: CareerNova API\nsdk: docker\napp_port: 7860\n---\n\nCareerNova FastAPI backend. Configure production secrets before starting. This repository contains code only; private account data is stored in PostgreSQL.\n',encoding='utf-8')
    archive=root/'.deploy'/'careernova-backend.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as zipped:
        for source in destination.iterdir():zipped.write(source,source.name)
    print(f'Prepared {len(list(destination.iterdir()))} backend files. Secrets, databases, resumes and job datasets excluded.')
    print('Bundle: .deploy/careernova-backend.zip')


if __name__=='__main__':build_bundle()
