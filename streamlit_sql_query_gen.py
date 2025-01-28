import requests
import cx_Oracle
import json
from configparser import ConfigParser
import logging
from string import Template

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TemplateQueryClient:
    def __init__(self, api_base_url, config_file='config.ini'):
        self.api_base_url = api_base_url
        self.config_file = config_file
        self.db_connection = None
        
    def load_db_config(self, section='oracle'):
        """Load database configuration from config file"""
        parser = ConfigParser()
        parser.read(self.config_file)
        
        db_config = {}
        if parser.has_section(section):
            params = parser.items(section)
            for param in params:
                db_config[param[0]] = param[1]
        else:
            raise Exception(f'Section {section} not found in {self.config_file}')
        
        return db_config

    def get_db_connection(self):
        """Establish database connection"""
        if not self.db_connection:
            try:
                config = self.load_db_config()
                self.db_connection = cx_Oracle.connect(
                    user=config['user'],
                    password=config['password'],
                    dsn=config['dsn']
                )
            except Exception as e:
                logger.error(f"Database connection error: {str(e)}")
                raise
        return self.db_connection

    def fetch_template(self, template_id):
        """Fetch template from REST API"""
        try:
            url = f"{self.api_base_url}/api/template/{template_id}"
            response = requests.get(url)
            response.raise_for_status()
            
            return response.json()['data']
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching template: {str(e)}")
            if response.status_code == 404:
                raise Exception(f"Template ID {template_id} not found")
            raise

    def get_variable_values(self, variables):
        """Get variable values from user input"""
        if not variables:
            return {}
            
        # Parse variables string into list if it's a JSON string
        if isinstance(variables, str):
            try:
                variables = json.loads(variables)
            except json.JSONDecodeError:
                variables = [v.strip() for v in variables.strip('[]').split(',')]

        values = {}
        print("\nPlease enter values for the following variables:")
        for var in variables:
            var = var.strip().strip('"\'')
            value = input(f"{var}: ")
            values[var] = value
        return values

    def execute_query(self, sql_query, variables):
        """Execute the SQL query with provided variables"""
        try:
            connection = self.get_db_connection()
            cursor = connection.cursor()

            # Substitute variables in the query
            query_template = Template(sql_query)
            final_query = query_template.safe_substitute(variables)

            logger.info(f"Executing query: {final_query}")
            cursor.execute(final_query)

            # Fetch and format results
            columns = [col[0] for col in cursor.description]
            results = []
            for row in cursor:
                results.append(dict(zip(columns, row)))

            return results

        except cx_Oracle.Error as e:
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            if cursor:
                cursor.close()

    def close(self):
        """Close database connection"""
        if self.db_connection:
            self.db_connection.close()
            self.db_connection = None

def main():
    # Configuration
    API_BASE_URL = "http://localhost:5000"  # Update with your API URL
    
    client = TemplateQueryClient(API_BASE_URL)
    
    try:
        # Get template ID from user
        template_id = input("Enter template ID: ")
        
        # Fetch template from API
        template = client.fetch_template(template_id)
        print(f"\nFound template: {template['template_id']}")
        print(f"SQL Query: {template['sql_query']}")
        
        # Get variable values from user
        variables = client.get_variable_values(template['variables'])
        
        # Execute query
        results = client.execute_query(template['sql_query'], variables)
        
        # Display results
        print("\nQuery Results:")
        if not results:
            print("No results found.")
        else:
            # Print column headers
            headers = results[0].keys()
            for header in headers:
                print(f"{header:<20}", end='')
            print("\n" + "-" * (20 * len(headers)))
            
            # Print rows
            for row in results:
                for value in row.values():
                    print(f"{str(value):<20}", end='')
                print()
                
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        
    finally:
        client.close()

if __name__ == "__main__":
    main()
