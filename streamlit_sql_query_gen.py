from flask import Flask, jsonify
import cx_Oracle
from configparser import ConfigParser
import logging
import os
from flasgger import Swagger, swag_from

# Initialize Flask app
app = Flask(__name__)

# Configure Swagger
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs"
}

swagger = Swagger(app, config=swagger_config, template={
    "swagger": "2.0",
    "info": {
        "title": "Template Query API",
        "description": "API for retrieving SQL queries and variables from templates",
        "version": "1.0.0",
        "contact": {
            "email": "your-email@example.com"
        }
    }
})

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load database configuration from config file
def load_db_config(filename='config.ini', section='oracle'):
    parser = ConfigParser()
    parser.read(filename)
    
    db_config = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db_config[param[0]] = param[1]
    else:
        raise Exception(f'Section {section} not found in {filename}')
    
    return db_config

# Database connection function
def get_db_connection():
    try:
        config = load_db_config()
        connection = cx_Oracle.connect(
            user=config['user'],
            password=config['password'],
            dsn=config['dsn']
        )
        return connection
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

@app.route('/api/template/<int:template_id>', methods=['GET'])
@swag_from({
    'tags': ['Templates'],
    'summary': 'Get template by ID',
    'parameters': [
        {
            'name': 'template_id',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': 'ID of the template to retrieve'
        }
    ],
    'responses': {
        200: {
            'description': 'Template found',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'example': 'success'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'template_id': {'type': 'integer', 'example': 1},
                            'sql_query': {'type': 'string', 'example': 'SELECT * FROM table'},
                            'variables': {'type': 'string', 'example': '["var1", "var2"]'}
                        }
                    }
                }
            }
        },
        404: {
            'description': 'Template not found',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'example': 'error'},
                    'message': {'type': 'string', 'example': 'Template ID not found'}
                }
            }
        },
        500: {
            'description': 'Internal server error',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'example': 'error'},
                    'message': {'type': 'string', 'example': 'Internal server error'}
                }
            }
        }
    }
})
def get_template(template_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Query to fetch template details
        query = """
            SELECT template_id, sql_query, variables
            FROM template_table
            WHERE template_id = :template_id
        """
        
        cursor.execute(query, {'template_id': template_id})
        result = cursor.fetchone()
        
        if result:
            template_data = {
                'template_id': result[0],
                'sql_query': result[1],
                'variables': result[2]  # Assuming variables are stored as a string
            }
            return jsonify({
                'status': 'success',
                'data': template_data
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': f'Template ID {template_id} not found'
            }), 404
            
    except Exception as e:
        logger.error(f"Error fetching template: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({
        'status': 'error',
        'message': 'Resource not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
