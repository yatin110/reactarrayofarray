import streamlit as st
import pandas as pd
import cx_Oracle
import re
import json
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title="SQL Template Manager",
    page_icon="📊",
    layout="wide"
)

# Database connection class
class OracleConnection:
    def __init__(self, username=None, password=None, host=None, port=None, service_name=None):
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.service_name = service_name
        self.connection = None
    
    def connect(self):
        dsn = cx_Oracle.makedsn(self.host, self.port, service_name=self.service_name)
        self.connection = cx_Oracle.connect(self.username, self.password, dsn)
        return self.connection
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def execute_query(self, query, params=None):
        if not self.connection:
            self.connect()
        
        cursor = self.connection.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith(('SELECT', 'WITH')):
                columns = [col[0] for col in cursor.description]
                data = cursor.fetchall()
                df = pd.DataFrame(data, columns=columns)
                return df
            else:
                self.connection.commit()
                return cursor.rowcount
        except Exception as e:
            self.connection.rollback()
            raise e
        finally:
            cursor.close()
    
    def get_tables(self):
        query = """
        SELECT table_name 
        FROM user_tables 
        ORDER BY table_name
        """
        return self.execute_query(query)
    
    def get_table_columns(self, table_name):
        query = """
        SELECT column_name, data_type 
        FROM user_tab_columns 
        WHERE table_name = :table_name 
        ORDER BY column_id
        """
        return self.execute_query(query, {'table_name': table_name.upper()})
    
    def get_templates(self):
        query = """
        SELECT template_id, template_name, description, created_date, 
               parent_template_id, is_parent
        FROM sql_templates
        ORDER BY template_name
        """
        try:
            return self.execute_query(query)
        except cx_Oracle.DatabaseError:
            # If table doesn't exist, create it
            self.create_template_tables()
            return pd.DataFrame(columns=['template_id', 'template_name', 'description', 'created_date', 'parent_template_id', 'is_parent'])
    
    def create_template_tables(self):
        # Create SQL templates table
        create_templates_table = """
        CREATE TABLE sql_templates (
            template_id NUMBER PRIMARY KEY,
            template_name VARCHAR2(200) NOT NULL,
            description VARCHAR2(1000),
            sql_query CLOB NOT NULL,
            template_config CLOB NOT NULL,
            created_date DATE DEFAULT SYSDATE,
            created_by VARCHAR2(100),
            parent_template_id NUMBER,
            is_parent NUMBER(1) DEFAULT 0,
            CONSTRAINT fk_parent_template FOREIGN KEY (parent_template_id) 
            REFERENCES sql_templates(template_id)
        )
        """
        
        # Create sequence for template_id
        create_sequence = """
        CREATE SEQUENCE sql_template_seq
        START WITH 1
        INCREMENT BY 1
        NOCACHE
        NOCYCLE
        """
        
        try:
            self.execute_query(create_templates_table)
            self.execute_query(create_sequence)
        except Exception as e:
            st.error(f"Error creating tables: {str(e)}")
    
    def save_template(self, template_name, description, sql_query, template_config, parent_template_id=None, is_parent=0):
        # Check if template table exists, if not create it
        try:
            self.execute_query("SELECT 1 FROM sql_templates WHERE ROWNUM = 1")
        except cx_Oracle.DatabaseError:
            self.create_template_tables()
        
        # Get next template ID
        query = "SELECT sql_template_seq.NEXTVAL FROM DUAL"
        template_id = self.execute_query(query).iloc[0, 0]
        
        # Insert template
        insert_query = """
        INSERT INTO sql_templates (
            template_id, template_name, description, sql_query, template_config, 
            created_by, parent_template_id, is_parent
        ) VALUES (
            :template_id, :template_name, :description, :sql_query, :template_config,
            :created_by, :parent_template_id, :is_parent
        )
        """
        
        params = {
            'template_id': template_id,
            'template_name': template_name,
            'description': description,
            'sql_query': sql_query,
            'template_config': template_config,
            'created_by': self.username,
            'parent_template_id': parent_template_id,
            'is_parent': is_parent
        }
        
        self.execute_query(insert_query, params)
        return template_id
    
    def update_template(self, template_id, template_name, description, sql_query, template_config):
        update_query = """
        UPDATE sql_templates
        SET template_name = :template_name,
            description = :description,
            sql_query = :sql_query,
            template_config = :template_config
        WHERE template_id = :template_id
        """
        
        params = {
            'template_id': template_id,
            'template_name': template_name,
            'description': description,
            'sql_query': sql_query,
            'template_config': template_config
        }
        
        self.execute_query(update_query, params)
    
    def get_template_by_id(self, template_id):
        query = """
        SELECT template_id, template_name, description, sql_query, template_config,
               created_date, parent_template_id, is_parent
        FROM sql_templates
        WHERE template_id = :template_id
        """
        return self.execute_query(query, {'template_id': template_id})
    
    def execute_template(self, sql_query):
        return self.execute_query(sql_query)

# SQL Query Builder class
class SQLQueryBuilder:
    def __init__(self):
        self.tables = []
        self.columns = []
        self.joins = []
        self.filters = []
        self.group_by = []
        self.aggregations = {}
    
    def add_table(self, table_name, alias=None):
        if alias:
            self.tables.append({"name": table_name, "alias": alias})
        else:
            self.tables.append({"name": table_name, "alias": table_name})
    
    def add_column(self, table_alias, column_name, display_name=None):
        self.columns.append({
            "table": table_alias,
            "column": column_name,
            "display": display_name if display_name else column_name
        })
    
    def add_join(self, from_table, from_column, to_table, to_column, join_type="INNER"):
        self.joins.append({
            "from_table": from_table,
            "from_column": from_column,
            "to_table": to_table,
            "to_column": to_column,
            "type": join_type
        })
    
    def add_filter(self, table, column, operator, value):
        self.filters.append({
            "table": table,
            "column": column,
            "operator": operator,
            "value": value
        })
    
    def add_group_by(self, table, column):
        self.group_by.append({
            "table": table,
            "column": column
        })
    
    def add_aggregation(self, table, column, function, display_name=None):
        key = f"{table}.{column}"
        self.aggregations[key] = {
            "table": table,
            "column": column,
            "function": function,
            "display": display_name if display_name else f"{function}_{column}"
        }
    
    def build_query(self):
        select_clause = []
        for col in self.columns:
            select_clause.append(f"{col['table']}.{col['column']} AS {col['display']}")
        
        for key, agg in self.aggregations.items():
            select_clause.append(
                f"{agg['function']}({agg['table']}.{agg['column']}) AS {agg['display']}"
            )
        
        if not select_clause:
            return "-- No columns selected"
        
        # FROM clause
        if not self.tables:
            return "-- No tables selected"
        
        from_clause = f"{self.tables[0]['name']} {self.tables[0]['alias']}"
        
        # JOIN clauses
        join_clauses = []
        for join in self.joins:
            join_clauses.append(
                f"{join['type']} JOIN {join['to_table']} ON "
                f"{join['from_table']}.{join['from_column']} = {join['to_table']}.{join['to_column']}"
            )
        
        # WHERE clause
        where_clauses = []
        for filt in self.filters:
            if filt['operator'] == 'IN':
                where_clauses.append(
                    f"{filt['table']}.{filt['column']} IN ({filt['value']})"
                )
            elif filt['operator'] == 'BETWEEN':
                values = filt['value'].split(' AND ')
                if len(values) == 2:
                    where_clauses.append(
                        f"{filt['table']}.{filt['column']} BETWEEN {values[0]} AND {values[1]}"
                    )
            else:
                where_clauses.append(
                    f"{filt['table']}.{filt['column']} {filt['operator']} {filt['value']}"
                )
        
        # GROUP BY clause
        group_by_clause = []
        for gb in self.group_by:
            group_by_clause.append(f"{gb['table']}.{gb['column']}")
        
        # Build the complete query
        query = f"SELECT\n    " + ",\n    ".join(select_clause)
        query += f"\nFROM {from_clause}"
        
        if join_clauses:
            query += "\n" + "\n".join(join_clauses)
        
        if where_clauses:
            query += "\nWHERE " + "\nAND ".join(where_clauses)
        
        if group_by_clause:
            query += "\nGROUP BY " + ", ".join(group_by_clause)
        
        return query
    
    def from_config(self, config):
        config_dict = json.loads(config)
        self.tables = config_dict.get('tables', [])
        self.columns = config_dict.get('columns', [])
        self.joins = config_dict.get('joins', [])
        self.filters = config_dict.get('filters', [])
        self.group_by = config_dict.get('group_by', [])
        self.aggregations = config_dict.get('aggregations', {})
    
    def to_config(self):
        return json.dumps({
            'tables': self.tables,
            'columns': self.columns,
            'joins': self.joins,
            'filters': self.filters,
            'group_by': self.group_by,
            'aggregations': self.aggregations
        })

# Initialize session state variables
if 'db_connected' not in st.session_state:
    st.session_state.db_connected = False

if 'db_connection' not in st.session_state:
    st.session_state.db_connection = None

if 'tables' not in st.session_state:
    st.session_state.tables = None

if 'query_builder' not in st.session_state:
    st.session_state.query_builder = SQLQueryBuilder()

if 'current_template_id' not in st.session_state:
    st.session_state.current_template_id = None

# App UI
st.title("SQL Template Manager")

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Connect to Database", "Template Manager", "Create Template", "Edit Template", "View Templates"])

# Database Connection
if page == "Connect to Database":
    st.header("Oracle Database Connection")
    
    with st.form("db_connection_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            host = st.text_input("Host", "localhost")
            
        with col2:
            port = st.text_input("Port", "1521")
            service_name = st.text_input("Service Name")
        
        submit_button = st.form_submit_button("Connect")
        
        if submit_button:
            try:
                db_conn = OracleConnection(
                    username=username,
                    password=password,
                    host=host,
                    port=port,
                    service_name=service_name
                )
                
                # Test connection
                db_conn.connect()
                st.success("Connected to Oracle database successfully!")
                
                # Get tables
                tables_df = db_conn.get_tables()
                st.session_state.tables = tables_df
                
                # Store connection
                st.session_state.db_connection = db_conn
                st.session_state.db_connected = True
                
                # Redirect to Template Manager
                st.experimental_rerun()
                
            except Exception as e:
                st.error(f"Connection failed: {str(e)}")
                st.session_state.db_connected = False
    
    if st.session_state.db_connected:
        st.success("You are connected to the database.")
        
        # Display tables
        if st.session_state.tables is not None:
            st.subheader("Available Tables")
            st.dataframe(st.session_state.tables)

# Template Manager
elif page == "Template Manager":
    if not st.session_state.db_connected:
        st.warning("Please connect to the database first.")
        st.sidebar.info("Go to 'Connect to Database' to establish connection.")
    else:
        st.header("Template Manager")
        
        # Get templates
        templates = st.session_state.db_connection.get_templates()
        
        # Display templates
        if not templates.empty:
            st.subheader("Available Templates")
            st.dataframe(templates)
            
            # Template actions
            col1, col2, col3 = st.columns(3)
            
            with col1:
                template_to_edit = st.selectbox(
                    "Select a template to edit",
                    options=templates['template_id'].tolist(),
                    format_func=lambda x: templates.loc[templates['template_id'] == x, 'template_name'].iloc[0]
                )
                if st.button("Edit Selected Template"):
                    st.session_state.current_template_id = template_to_edit
                    st.experimental_rerun()
            
            with col2:
                template_to_view = st.selectbox(
                    "Select a template to view",
                    options=templates['template_id'].tolist(),
                    format_func=lambda x: templates.loc[templates['template_id'] == x, 'template_name'].iloc[0],
                    key="view_template"
                )
                if st.button("View Selected Template"):
                    template_data = st.session_state.db_connection.get_template_by_id(template_to_view)
                    if not template_data.empty:
                        st.subheader(f"Template: {template_data['template_name'].iloc[0]}")
                        st.text_area("SQL Query", template_data['sql_query'].iloc[0], height=300)
                        
                        # Execute template
                        if st.button("Execute Template"):
                            try:
                                result = st.session_state.db_connection.execute_template(template_data['sql_query'].iloc[0])
                                st.success("Query executed successfully!")
                                st.dataframe(result)
                            except Exception as e:
                                st.error(f"Error executing query: {str(e)}")
            
            with col3:
                parent_templates = templates[templates['is_parent'] == 1]
                if not parent_templates.empty:
                    parent_template = st.selectbox(
                        "Select a parent template for a new child",
                        options=parent_templates['template_id'].tolist(),
                        format_func=lambda x: parent_templates.loc[parent_templates['template_id'] == x, 'template_name'].iloc[0]
                    )
                    if st.button("Create Child Template"):
                        st.session_state.parent_template_id = parent_template
                        st.experimental_rerun()
        else:
            st.info("No templates available. Create your first template!")
        
        # Buttons to create templates
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Create New Template"):
                st.session_state.current_template_id = None
                st.session_state.query_builder = SQLQueryBuilder()
                st.experimental_rerun()
        
        with col2:
            if st.button("Refresh Templates"):
                st.experimental_rerun()

# Create Template
elif page == "Create Template":
    if not st.session_state.db_connected:
        st.warning("Please connect to the database first.")
        st.sidebar.info("Go to 'Connect to Database' to establish connection.")
    else:
        st.header("Create SQL Template")
        
        # Check if creating a child template
        is_child_template = False
        parent_template_data = None
        
        if 'parent_template_id' in st.session_state:
            parent_id = st.session_state.parent_template_id
            parent_template_data = st.session_state.db_connection.get_template_by_id(parent_id)
            
            if not parent_template_data.empty:
                is_child_template = True
                st.info(f"Creating a child template based on: {parent_template_data['template_name'].iloc[0]}")
                
                # Load parent template config
                parent_config = parent_template_data['template_config'].iloc[0]
                parent_sql = parent_template_data['sql_query'].iloc[0]
                
                st.subheader("Parent Template SQL")
                st.code(parent_sql, language="sql")
        
        # Template details
        with st.form("template_details"):
            template_name = st.text_input("Template Name")
            description = st.text_area("Description")
            is_parent = st.checkbox("Mark as Parent Template")
            
            submit_button = st.form_submit_button("Next")
        
        if submit_button and template_name:
            # Continue to query builder
            st.session_state.template_name = template_name
            st.session_state.description = description
            st.session_state.is_parent = is_parent
            
            # Query Builder UI
            st.subheader("SQL Query Builder")
            
            if not is_child_template:
                # For parent templates - full query building
                tables_df = st.session_state.tables
                
                # Select tables
                selected_tables = st.multiselect(
                    "Select Tables",
                    options=tables_df['TABLE_NAME'].tolist()
                )
                
                if selected_tables:
                    query_builder = SQLQueryBuilder()
                    
                    # Add tables
                    for table in selected_tables:
                        query_builder.add_table(table)
                    
                    # Get columns for each table
                    all_columns = {}
                    for table in selected_tables:
                        columns_df = st.session_state.db_connection.get_table_columns(table)
                        all_columns[table] = columns_df
                    
                    # Select columns
                    st.subheader("Select Columns")
                    for table in selected_tables:
                        st.write(f"**Table: {table}**")
                        columns = all_columns[table]
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            selected_cols = st.multiselect(
                                f"Columns from {table}",
                                options=columns['COLUMN_NAME'].tolist(),
                                key=f"cols_{table}"
                            )
                            
                            for col in selected_cols:
                                query_builder.add_column(table, col)
                        
                        with col2:
                            agg_cols = st.multiselect(
                                f"Aggregate columns from {table}",
                                options=columns['COLUMN_NAME'].tolist(),
                                key=f"agg_{table}"
                            )
                            
                            for col in agg_cols:
                                agg_func = st.selectbox(
                                    f"Aggregation for {col}",
                                    options=["SUM", "AVG", "COUNT", "MAX", "MIN"],
                                    key=f"agg_func_{table}_{col}"
                                )
                                query_builder.add_aggregation(table, col, agg_func)
                                
                                if agg_func != "COUNT":
                                    query_builder.add_group_by(table, col)
                    
                    # Joins
                    if len(selected_tables) > 1:
                        st.subheader("Define Joins")
                        
                        for i in range(len(selected_tables) - 1):
                            st.write(f"Join {i+1}")
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                from_table = st.selectbox(
                                    "From Table",
                                    options=selected_tables,
                                    key=f"from_table_{i}"
                                )
                                
                                from_cols = all_columns[from_table]['COLUMN_NAME'].tolist()
                                from_col = st.selectbox(
                                    "From Column",
                                    options=from_cols,
                                    key=f"from_col_{i}"
                                )
                            
                            with col2:
                                join_type = st.selectbox(
                                    "Join Type",
                                    options=["INNER", "LEFT", "RIGHT", "FULL"],
                                    key=f"join_type_{i}"
                                )
                            
                            with col3:
                                to_table = st.selectbox(
                                    "To Table",
                                    options=[t for t in selected_tables if t != from_table],
                                    key=f"to_table_{i}"
                                )
                                
                                to_cols = all_columns[to_table]['COLUMN_NAME'].tolist()
                                to_col = st.selectbox(
                                    "To Column",
                                    options=to_cols,
                                    key=f"to_col_{i}"
                                )
                            
                            if st.button("Add Join", key=f"add_join_{i}"):
                                query_builder.add_join(from_table, from_col, to_table, to_col, join_type)
                    
                    # Generate SQL Query
                    if st.button("Generate SQL"):
                        sql_query = query_builder.build_query()
                        st.session_state.generated_sql = sql_query
                        st.session_state.query_builder = query_builder
                    
                    if 'generated_sql' in st.session_state:
                        st.subheader("Generated SQL")
                        st.code(st.session_state.generated_sql, language="sql")
                        
                        # Save template
                        if st.button("Save Template"):
                            try:
                                template_config = st.session_state.query_builder.to_config()
                                template_id = st.session_state.db_connection.save_template(
                                    st.session_state.template_name,
                                    st.session_state.description,
                                    st.session_state.generated_sql,
                                    template_config,
                                    None,
                                    1 if st.session_state.is_parent else 0
                                )
                                
                                st.success(f"Template saved successfully with ID: {template_id}")
                                
                                # Reset state
                                if 'generated_sql' in st.session_state:
                                    del st.session_state.generated_sql
                                if 'query_builder' in st.session_state:
                                    st.session_state.query_builder = SQLQueryBuilder()
                                
                                # Redirect to template manager
                                st.experimental_rerun()
                                
                            except Exception as e:
                                st.error(f"Error saving template: {str(e)}")
            else:
                # For child templates - derive from parent
                st.write("Child templates use the same tables as their parent.")
                
                # Load parent config
                parent_config = parent_template_data['template_config'].iloc[0]
                parent_builder = SQLQueryBuilder()
                parent_builder.from_config(parent_config)
                
                # Allow modifying filters
                st.subheader("Modify Filters")
                
                # Display tables and columns from parent
                for table in parent_builder.tables:
                    table_name = table['name']
                    columns_df = st.session_state.db_connection.get_table_columns(table_name)
                    
                    st.write(f"**Table: {table_name}**")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        filter_col = st.selectbox(
                            f"Column from {table_name}",
                            options=columns_df['COLUMN_NAME'].tolist(),
                            key=f"filter_col_{table_name}"
                        )
                    
                    with col2:
                        operator = st.selectbox(
                            "Operator",
                            options=["=", "<>", ">", "<", ">=", "<=", "IN", "LIKE", "BETWEEN"],
                            key=f"filter_op_{table_name}"
                        )
                    
                    with col3:
                        filter_value = st.text_input(
                            "Value",
                            key=f"filter_val_{table_name}"
                        )
                    
                    if st.button(f"Add Filter for {table_name}"):
                        parent_builder.add_filter(table_name, filter_col, operator, filter_value)
                
                # Generate child SQL
                if st.button("Generate Child SQL"):
                    child_sql = parent_builder.build_query()
                    st.session_state.generated_sql = child_sql
                    st.session_state.query_builder = parent_builder
                
                if 'generated_sql' in st.session_state:
                    st.subheader("Generated SQL")
                    st.code(st.session_state.generated_sql, language="sql")
                    
                    # Save child template
                    if st.button("Save Child Template"):
                        try:
                            template_config = st.session_state.query_builder.to_config()
                            template_id = st.session_state.db_connection.save_template(
                                st.session_state.template_name,
                                st.session_state.description,
                                st.session_state.generated_sql,
                                template_config,
                                parent_id,
                                0  # Child is never a parent
                            )
                            
                            st.success(f"Child template saved successfully with ID: {template_id}")
                            
                            # Reset state
                            if 'generated_sql' in st.session_state:
                                del st.session_state.generated_sql
                            if 'parent_template_id' in st.session_state:
                                del st.session_state.parent_template_id
                            
                            # Redirect to template manager
                            st.experimental_rerun()
                            
                        except Exception as e:
                            st.error(f"Error saving child template: {str(e)}")

# Edit Template
elif page == "Edit Template":
    if not st.session_state.db_connected:
        st.warning("Please connect to the database first.")
        st.sidebar.info("Go to 'Connect to Database' to establish connection.")
    elif 'current_template_id' not in st.session_state or st.session_state.current_template_id is None:
        st.warning("No template selected for editing.")
        st.sidebar.info("Go to 'Template Manager' to select a template to edit.")
    else:
        st.header("Edit SQL Template")
        
        # Get template data
        template_id = st.session_state.current_template_id
        template_data = st.session_state.db_connection.get_template_by_id(template_id)
        
        if not template_data.empty:
            template_name = template_data['template_name'].iloc[0]
            description = template_data['description'].iloc[0]
            sql_query = template_data['sql_query'].iloc[0]
            template_config = template_data['template_config'].iloc[0]
            
            st.write(f"Editing template: **{template_name}**")
            
            # Load template config
            query_builder = SQLQueryBuilder()
            query_builder.from_config(template_config)
            
            # Template details
            with st.form("edit_template_details"):
                new_name = st.text_input("Template Name", value=template_name)
                new_description = st.text_area("Description", value=description)
                
                submit_button = st.form_submit_button("Update Details")
            
            if submit_button:
                # Update template basic details
                st.session_state.template_name = new_name
                st.session_state.description = new_description
            
            # Show current SQL
            st.subheader("Current SQL Query")
            st.code(sql_query, language="sql")
            
            # Edit SQL directly
            st.subheader("Edit SQL")
            new_sql = st.text_area("SQL Query", value=sql_query, height=300)
            
            if st.button("Save Changes"):
                try:
                    st.session_state.db_connection.update_template(
                        template_id,
                        st.session_state.template_name if 'template_name' in st.session_state else template_name,
                        st.session_state.description if 'description' in st.session_state else description,
                        new_sql,
                        template_config
                    )
                    
                    st.success("Template updated successfully!")
                    
                    # Reset state
                    st.session_state.current_template_id = None
                    
                    # Redirect to template manager
                    st.experimental_rerun()
                    
                except Exception as e:
                    st.error(f"Error updating template: {str(e)}")
        else:
            st.error("Template not found.")

# View Templates
elif page == "View Templates":
    if not st.session_state.db_connected:
        st.warning("Please connect to the database first.")
        st.sidebar.info("Go to 'Connect to Database' to establish connection.")
    else:
        st.header("View SQL Templates")
        
        # Get templates
        templates = st.session_state.db_connection.get_templates()
        
        if not templates.empty:
            # Template selection
            selected_template = st.selectbox(
                "Select a template to view",
                options=templates['template_id'].tolist(),
                format_func=lambda x: templates.loc[templates['template_id'] == x, 'template_name'].iloc[0]
            )
            
            if selected_template:
                template_data = st.session_state.db_connection.get_template_by_id(selected_template)
                
                if not template_data.empty:
                    # Display template details
                    st.subheader(f"Template: {template_data['template_name'].iloc[0]}")
                    st.write(f"**Description:** {template_data['description'].iloc[0]}")
                    
                    # Check if it's a parent template
                    is_parent = template_data['is_parent'].iloc[0]
                    if is_parent:
                        st.info("This is a parent template that can be used as a base for child templates.")
                    
                    # Check if it's a child template
                    parent_id = template_data['parent_template_id'].iloc[0]
                    if parent_id:
                        parent_data = st.session_state.db_connection.get_template_by_id(parent_id)
                        if not parent_data.empty:
                            st.info(f"This is a child template based on: {parent_data['template_name'].iloc[0]}")
                    
                    # Display SQL
                    st.subheader("SQL Query")
                    st.code(template_data['sql_query'].iloc[0], language="sql")
                    
                    # Execute template
                    if st.button("Execute Template"):
                        try:
                            result = st.session_state.db_connection.execute_template(template_data['sql_query'].iloc[0])
                            st.success("Query executed successfully!")
                            st.dataframe(result)
                            
                            # Allow exporting results
                            csv = result.to_csv(index=False)
                            st.download_button(
                                label="Download results as CSV",
                                data=csv,
                                file_name=f"{template_data['template_name'].iloc[0]}_results.csv",
                                mime="text/csv"
                            )
                        except Exception as e:
                            st.error(f"Error executing query: {str(e)}")
        else:
            st.info("No templates available. Create your first template!")

# Main page (default)
else:
    st.header("Welcome to SQL Template Manager")
    st.write("""
    This application allows you to manage SQL query templates for your Oracle database. 
    You can create, edit, and view SQL templates that can be reused in your organization.
    
    ## Features
    
    - Connect to Oracle database
    - Create SQL templates visually without writing SQL
    - Define joins, aggregations, and filters
    - Parent and child template support
    - Execute templates directly and view results
    
    ## Getting Started
    
    1. Connect to your Oracle database from the sidebar
    2. Create a new template or view existing ones
    3. Execute templates to see results
    """)
    
    # Quick actions
    st.subheader("Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Connect to Database"):
            st.experimental_rerun()
    
    with col2:
        if st.button("Create Template"):
            st.experimental_rerun()
    
    with col3:
        if st.button("View Templates"):
            st.experimental_rerun()

# Disconnect from database when app is closed
def disconnect_db():
    if st.session_state.db_connection:
        st.session_state.db_connection.disconnect()

# Register the disconnect function to be called when the app is closed
st.experimental_set_query_params()
