"""Start the local service without interrupting unrelated processes."""
import os
from pathlib import Path
import uvicorn
from copy import deepcopy
from uvicorn.config import LOGGING_CONFIG

if __name__ == '__main__':
    os.chdir(Path(__file__).resolve().parent)
    config = deepcopy(LOGGING_CONFIG)
    for name, filename, level in [('project_file', 'srv.log', 'INFO'), ('project_errors', 'srv.err', 'ERROR')]:
        config['handlers'][name] = {'class': 'logging.FileHandler', 'filename': filename,
                                    'formatter': 'default', 'level': level, 'encoding': 'utf-8'}
    for name in ('uvicorn', 'uvicorn.access'):
        config['loggers'][name]['handlers'] += ['project_file', 'project_errors']
    print('Camera:', os.getenv('CAMERA_URL', 'not configured (/verify still works)'))
    print('Set CAMERA_TOKEN in the environment if the camera requires it.')
    uvicorn.run('server:app', host=os.getenv('SERVER_HOST', '127.0.0.1'),
                port=int(os.getenv('SERVER_PORT', '8000')), log_config=config)
