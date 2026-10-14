"""
Robust transformation of backend/app/api/v1/projects.py to inject current_user and user_id.
"""
import re

with open('backend/app/api/v1/projects.py', 'r', encoding='utf-8') as f:
    text = f.read().replace('\r\n', '\n')

# Split by function definitions
# Functions start with @router.
parts = re.split(r'(\n@router\.[a-z]+\()', text)

new_parts = [parts[0]] # header / imports

for i in range(1, len(parts), 2):
    router_prefix = parts[i]
    func_body = parts[i+1]
    
    # Check if this function takes project_id
    # Signature is between router_prefix and "):"
    header_match = re.search(r'async def ([a-zA-Z0-9_]+)\((.*?)\)\s*(?:->.*?)?:', func_body, re.DOTALL)
    if header_match:
        func_name = header_match.group(1)
        params = header_match.group(2)
        
        if 'project_id' in params and 'current_user' not in params:
            # 1. Inject current_user before db: AsyncSession = Depends(get_db)
            if 'db: AsyncSession = Depends(get_db)' in params:
                new_params = params.replace(
                    'db: AsyncSession = Depends(get_db)',
                    'current_user: User = Depends(get_current_user_or_default),\n    db: AsyncSession = Depends(get_db)'
                )
                func_body = func_body[:header_match.start(2)] + new_params + func_body[header_match.end(2):]
            
            # 2. Update service calls inside this function
            # Match await project_service.get_project(project_id, db)
            func_body = func_body.replace(
                'await project_service.get_project(project_id, db)',
                'await project_service.get_project(project_id, db, user_id=current_user.id)'
            )
            # Match (project_id, db)
            func_body = re.sub(
                r'await project_service\.([a-zA-Z0-9_]+)\(project_id,\s*db\)',
                r'await project_service.\1(project_id, db, user_id=current_user.id)',
                func_body
            )
            # Match (project_id=project_id, ... db=db)
            # If db=db, is in a project_service call, append user_id=current_user.id,
            func_body = re.sub(
                r'(await project_service\.[a-zA-Z0-9_]+\([^)]*?db=db,)',
                r'\1\n        user_id=current_user.id,',
                func_body,
                flags=re.DOTALL
            )
    
    new_parts.append(router_prefix)
    new_parts.append(func_body)

transformed = ''.join(new_parts)

import ast
ast.parse(transformed)
print("AST parsed transformed projects.py successfully!")

with open('backend/app/api/v1/projects.py', 'w', encoding='utf-8') as f:
    f.write(transformed)

print("Saved backend/app/api/v1/projects.py!")
