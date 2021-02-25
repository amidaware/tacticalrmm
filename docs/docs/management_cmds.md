# Management Commands

To run any of the management commands you must first activate the python virtual env:
```bash
cd /rmm/api/tacticalrmm
source ../env/bin/activate
```

#### Reset a user's password
```bash
python manage.py reset_password <username>
```

#### Reset a user's 2fa token
```bash
python manage.py reset_2fa <username>
```

#### Find all agents that have X software installed
```bash
python manage.py find_software "adobe"
```

#### Show outdated online agents
```bash
python manage.py show_outdated_agents
```

#### Log out all active web sessions
```bash
python manage.py delete_tokens
```

#### Check for orphaned tasks on all agents and remove them
```bash
python manage.py remove_orphaned_tasks
```

#### Create a MeshCentral agent invite link
```bash
python manage.py get_mesh_exe_url
```