import io
import zipfile
import httpx

BASE_URL = 'http://127.0.0.1:8000/api/v1'
client = httpx.Client(timeout=30.0)

print('--- Test 1: Python Project ZIP ---')
p1_create = client.post(f'{BASE_URL}/projects', json={'name': 'PyProjectTest', 'source_type': 'zip'}).json()
p1_id = p1_create['id']
print('Created Project:', p1_id)

buf = io.BytesIO()
with zipfile.ZipFile(buf, 'w') as zf:
    zf.writestr('main.py', 'print("hello python world")\n')
    zf.writestr('app/utils.py', 'def add(a, b): return a + b\n')
    zf.writestr('node_modules/bad.js', 'console.log("should be ignored");\n')
    zf.writestr('__pycache__/cached.pyc', 'compiled byte code')
buf.seek(0)

upload_res = client.post(
    f'{BASE_URL}/projects/{p1_id}/upload',
    files={'file': ('python_project.zip', buf.getvalue(), 'application/zip')}
)
print('Upload status code:', upload_res.status_code)
assert upload_res.status_code == 200, f'Upload failed: {upload_res.text}'
p1_uploaded = upload_res.json()
print('Status:', p1_uploaded['status'])
assert p1_uploaded['status'] == 'READY'

files_res = client.get(f'{BASE_URL}/projects/{p1_id}/files').json()
file_paths = [f['path'] for f in files_res['files']]
print('Extracted files count:', files_res['total_files'], 'Paths:', file_paths)
assert files_res['total_files'] == 2, 'Ignored files were not excluded!'
print('Test 1 PASSED!\n')

print('--- Test 2: JavaScript/TypeScript Project ZIP ---')
p2_create = client.post(f'{BASE_URL}/projects', json={'name': 'TsProjectTest', 'source_type': 'zip'}).json()
p2_id = p2_create['id']

buf_ts = io.BytesIO()
with zipfile.ZipFile(buf_ts, 'w') as zf:
    zf.writestr('package.json', '{"name": "test-pkg", "version": "1.0.0"}\n')
    zf.writestr('src/index.ts', 'export const greet = (name: string) => `Hello ${name}`;\n')
    zf.writestr('dist/bundle.js', 'built bundle')
buf_ts.seek(0)

upload_ts_res = client.post(
    f'{BASE_URL}/projects/{p2_id}/upload',
    files={'file': ('ts_project.zip', buf_ts.getvalue(), 'application/zip')}
)
assert upload_ts_res.status_code == 200, f'Upload failed: {upload_ts_res.text}'
files_ts = client.get(f'{BASE_URL}/projects/{p2_id}/files').json()
print('TS Extracted files count:', files_ts['total_files'])
assert files_ts['total_files'] == 2
print('Test 2 PASSED!\n')

print('--- Test 3: Public GitHub Repository Clone ---')
p3_create = client.post(
    f'{BASE_URL}/projects',
    json={'name': 'OctocatTest', 'source_type': 'git', 'source_url': 'https://github.com/octocat/Hello-World'}
).json()
p3_id = p3_create['id']
clone_res = client.post(f'{BASE_URL}/projects/{p3_id}/clone', json={'source_url': 'https://github.com/octocat/Hello-World'})
print('Clone status code:', clone_res.status_code, clone_res.json().get('status'))
assert clone_res.status_code == 200
assert clone_res.json()['status'] == 'READY'
files_git = client.get(f'{BASE_URL}/projects/{p3_id}/files').json()
print('Git files count:', files_git['total_files'])
assert files_git['total_files'] > 0
print('Test 3 PASSED!\n')

print('--- Test 4: Invalid ZIP Upload ---')
p4_create = client.post(f'{BASE_URL}/projects', json={'name': 'InvalidZipTest', 'source_type': 'zip'}).json()
p4_id = p4_create['id']
bad_buf = b'not a zip file content'
bad_upload = client.post(
    f'{BASE_URL}/projects/{p4_id}/upload',
    files={'file': ('fake.zip', bad_buf, 'application/zip')}
)
print('Invalid zip response code:', bad_upload.status_code)
assert bad_upload.status_code == 400
print('Test 4 PASSED!\n')

print('--- Test 5: Invalid GitHub URL ---')
p5_create = client.post(f'{BASE_URL}/projects', json={'name': 'BadGitTest', 'source_type': 'git'}).json()
p5_id = p5_create['id']
bad_clone = client.post(f'{BASE_URL}/projects/{p5_id}/clone', json={'source_url': 'https://gitlab.com/notgithub/repo'})
print('Bad git response code:', bad_clone.status_code)
assert bad_clone.status_code == 400
print('Test 5 PASSED!\n')

print('--- Test 6: Project Deletion ---')
del_res = client.delete(f'{BASE_URL}/projects/{p1_id}')
assert del_res.status_code in (200, 204), f'Expected 200/204 but got {del_res.status_code}'
get_del = client.get(f'{BASE_URL}/projects/{p1_id}')

assert get_del.status_code == 404
print('Project successfully deleted and confirmed 404!')
print('Test 6 PASSED!\n')

# Cleanup other test projects
for pid in [p2_id, p3_id, p4_id, p5_id]:
    client.delete(f'{BASE_URL}/projects/{pid}')
print('ALL 6 LIVE SCENARIOS COMPLETED AND PASSED WITH FLYING COLORS!')
