import config
import os
from app import create_app

app = create_app()

@app.context_processor
def inject_config():
    return dict(config=config)

if __name__ == "__main__":

    is_debug = os.getenv('FLASK_ENV') == 'development'
    
    app.run(
        debug=is_debug, 
        port=config.web_app_port, 
        host=config.web_app_host
    )