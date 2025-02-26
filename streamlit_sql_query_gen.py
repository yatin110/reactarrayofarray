import streamlit as st
import cx_Oracle
import pandas as pd
import json
from datetime import datetime
import re

# Set page configuration
st.set_page_config(
    page_title="SQL Template Generator",
    page_title_align="center",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Application state
if 'connection' not in st.session_state:
    st.session_state.connection = None
if 'tables' not in st.session_state:
    st.session_state.tables = []
if 'selected_tables' not in st.session_state:
    st.session_state.selected_tables = []
if 'columns_info' not in st.session_state:
    st.session_state.columns_info = {}
if 'joins' not in st.session_state:
    st.session_state.joins = []
if 'selected_columns' not in st.session_state:
    st.session_state.selected_columns = []
if 'aggregations' not in st.session_state:
    st.session_state.aggregations = {}
if 'group_by_columns' not in st.session_state:
    st.session_state.group_by_columns = []
if 'templates' not in st.session_state:
    st.session_state.templates = []
if 'is_child_template' not in st.session_state:
    st.session_state.is_child_template = False
if 'parent_template_id' not in st.session_state:
    st.session_state.parent_template_id = None
if 'parent_derived_table' not in st.session_state:
    st.session_state.parent_derived_table = None
if 'parent_columns' not in st.session_state:
    st.session_state.parent_columns = []
if 'where_conditions' not in st.session_state:
    st.session_state.where_conditions = []
if 'filter_values' not in st.session_state:
    st.session_state.filter_values = {}

# Database connection function
def connect_to_oracle(username, password, dsn):
    try:
        connection = cx_Oracle.connect(
            user=username,
            password=password,
            dsn=dsn
        )
        return connection, "Connected successfully to Oracle database!"
    except Exception as e:
        return None, f"Error connecting to database: {e}"

# Get all tables from Oracle database
def get_tables(connection):
    cursor = connection.cursor()
    cursor.execute("""
        SELECT table_name 
        FROM user_tables 
        ORDER BY table_name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables

# Get columns for a specific table
def get_columns(connection, table_name):
    cursor = connection.cursor()
    cursor.execute(f"""
        SELECT column_name, data_type
        FROM user_tab_columns
        WHERE table_name = '{table_name}'
        ORDER BY column_id
    """)
    columns = [(row[0], row[1]) for row in cursor.fetchall()]
    cursor.close()
    return columns

# Get columns from a SQL query
def get_columns_from_query(connection, sql_query):
    cursor = connection.cursor()
    try:
        # Add a WHERE 1=0 to avoid actually fetching data
        modified_query = f"SELECT * FROM ({sql_query}) WHERE 1=0"
        cursor.execute(modified_query)
        columns = [(col[0], str(col[1])) for col in cursor.description]
        return columns
    except Exception as e:
        st.error(f"Error getting columns from query: {e}")
        return []
    finally:
        cursor.close()

# Save template to database
def save_template(connection, template_name, sql_query, metadata, parent_id=None):
    cursor = connection.cursor()
    try:
        # Check if SQL_TEMPLATES table exists, if not create it
        cursor.execute("""
            SELECT count(*) 
            FROM user_tables 
            WHERE table_name = 'SQL_TEMPLATES'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                CREATE TABLE SQL_TEMPLATES (
                    template_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    template_name VARCHAR2(100) NOT NULL,
                    sql_query CLOB NOT NULL,
                    metadata CLOB NOT NULL,
                    parent_id NUMBER NULL,
                    created_date DATE DEFAULT SYSDATE,
                    modified_date DATE DEFAULT SYSDATE,
                    CONSTRAINT fk_parent_template FOREIGN KEY (parent_id) 
                        REFERENCES SQL_TEMPLATES(template_id) ON DELETE CASCADE
                )
            """)
            connection.commit()
        
        # Check if template name already exists
        cursor.execute("""
            SELECT template_id 
            FROM SQL_TEMPLATES 
            WHERE template_name = :name
        """, name=template_name)
        
        result = cursor.fetchone()
        if result:
            # Update existing template
            template_id = result[0]
            cursor.execute("""
                UPDATE SQL_TEMPLATES 
                SET sql_query = :query, 
                    metadata = :metadata,
                    parent_id = :parent_id,
                    modified_date = SYSDATE
                WHERE template_id = :id
            """, query=sql_query, metadata=metadata, parent_id=parent_id, id=template_id)
            message = f"Template '{template_name}' updated successfully!"
        else:
            # Insert new template
            cursor.execute("""
                INSERT INTO SQL_TEMPLATES (template_name, sql_query, metadata, parent_id)
                VALUES (:name, :query, :metadata, :parent_id)
            """, name=template_name, query=sql_query, metadata=metadata, parent_id=parent_id)
            message = f"Template '{template_name}' saved successfully!"
        
        connection.commit()
        return True, message
    except Exception as e:
        connection.rollback()
        return False, f"Error saving template: {e}"
    finally:
        cursor.close()

# Get all templates from database
def get_templates(connection):
    cursor = connection.cursor()
    try:
        # Check if SQL_TEMPLATES table exists
        cursor.execute("""
            SELECT count(*) 
            FROM user_tables 
            WHERE table_name = 'SQL_TEMPLATES'
        """)
        if cursor.fetchone()[0] == 0:
            return []
        
        cursor.execute("""
            SELECT template_id, template_name, sql_query, metadata, parent_id
            FROM SQL_TEMPLATES
            ORDER BY template_name
        """)
        templates = [
            {
                "id": row[0], 
                "name": row[1], 
                "query": row[2], 
                "metadata": json.loads(row[3]),
                "parent_id": row[4]
            } 
            for row in cursor.fetchall()
        ]
        return templates
    except Exception as e:
        st.error(f"Error fetching templates: {e}")
        return []
    finally:
        cursor.close()

# Get a specific template by ID
def get_template_by_id(connection, template_id):
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT template_id, template_name, sql_query, metadata, parent_id
            FROM SQL_TEMPLATES
            WHERE template_id = :id
        """, id=template_id)
        
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0], 
                "name": row[1], 
                "query": row[2], 
                "metadata": json.loads(row[3]),
                "parent_id": row[4]
            }
        return None
    except Exception as e:
        st.error(f"Error fetching template: {e}")
        return None
    finally:
        cursor.close()

# Get all parent templates (templates that have no parent)
def get_parent_templates(templates):
    return [t for t in templates if t["parent_id"] is None]

# Get all child templates for a specific parent
def get_child_templates(templates, parent_id):
    return [t for t in templates if t["parent_id"] == parent_id]

# Generate SQL query based on user selections for parent templates
def generate_parent_sql_query():
    if not st.session_state.selected_tables:
        return "No tables selected"
    
    # Select clause
    select_parts = []
    for col in st.session_state.selected_columns:
        table_name, column_name = col.split(".")
        if col in st.session_state.aggregations and st.session_state.aggregations[col]:
            agg_func = st.session_state.aggregations[col]
            select_parts.append(f"{agg_func}({table_name}.{column_name}) AS {agg_func}_{column_name}")
        else:
            select_parts.append(f"{table_name}.{column_name}")
    
    select_clause = "SELECT " + ",\n       ".join(select_parts)
    
    # From clause
    from_clause = f"FROM {st.session_state.selected_tables[0]}"
    
    # Join clause
    join_clause = ""
    for join in st.session_state.joins:
        source_table, source_column = join["source"].split(".")
        target_table, target_column = join["target"].split(".")
        join_clause += f"\nJOIN {target_table} ON {source_table}.{source_column} = {target_table}.{target_column}"
    
    # Where clause (placeholder for future filters)
    where_clause = ""
    
    # Group by clause
    group_by_clause = ""
    if st.session_state.group_by_columns:
        group_by_parts = []
        for col in st.session_state.group_by_columns:
            table_name, column_name = col.split(".")
            group_by_parts.append(f"{table_name}.{column_name}")
        
        group_by_clause = "\nGROUP BY " + ",\n         ".join(group_by_parts)
    
    # Complete SQL query
    sql_query = f"{select_clause}\n{from_clause}{join_clause}{where_clause}{group_by_clause}"
    
    return sql_query

# Generate SQL query for child templates
def generate_child_sql_query():
    if not st.session_state.parent_template_id or not st.session_state.parent_derived_table:
        return "No parent template selected"
    
    # Select clause
    select_parts = []
    for col in st.session_state.selected_columns:
        column_name = col  # No table prefix needed as all columns come from the derived table
        if col in st.session_state.aggregations and st.session_state.aggregations[col]:
            agg_func = st.session_state.aggregations[col]
            select_parts.append(f"{agg_func}({column_name}) AS {agg_func}_{column_name}")
        else:
            select_parts.append(f"{column_name}")
    
    select_clause = "SELECT " + ",\n       ".join(select_parts)
    
    # Get parent query
    parent_template = get_template_by_id(st.session_state.connection, st.session_state.parent_template_id)
    parent_query = parent_template["query"]
    
    # From clause with parent query as subquery
    derived_table = st.session_state.parent_derived_table
    from_clause = f"FROM ({parent_query}) {derived_table}"
    
    # Where clause
    where_clause = ""
    if st.session_state.where_conditions:
        conditions = []
        for condition in st.session_state.where_conditions:
            column = condition["column"]
            operator = condition["operator"]
            
            # Different handling based on operator type
            if operator in ("IS NULL", "IS NOT NULL"):
                conditions.append(f"{column} {operator}")
            else:
                # Format value based on data type
                value_placeholder = condition["value_placeholder"]
                conditions.append(f"{column} {operator} {value_placeholder}")
        
        where_clause = "\nWHERE " + " AND ".join(conditions)
    
    # Group by clause
    group_by_clause = ""
    if st.session_state.group_by_columns:
        group_by_parts = []
        for col in st.session_state.group_by_columns:
            group_by_parts.append(col)
        
        group_by_clause = "\nGROUP BY " + ",\n         ".join(group_by_parts)
    
    # Complete SQL query
    sql_query = f"{select_clause}\n{from_clause}{where_clause}{group_by_clause}"
    
    # Replace parameter placeholders with actual values for display
    display_query = sql_query
    for col, value in st.session_state.filter_values.items():
        if value:
            # Check if the value needs quotes (string types)
            if isinstance(value, str):
                value_str = f"'{value}'"
            else:
                value_str = str(value)
                
            # Replace the placeholder in the display query
            placeholder = f":param_{col.replace('.', '_')}"
            display_query = display_query.replace(placeholder, value_str)
    
    return display_query

# Reset the query builder for parent template
def reset_parent_query_builder():
    st.session_state.selected_tables = []
    st.session_state.joins = []
    st.session_state.selected_columns = []
    st.session_state.aggregations = {}
    st.session_state.group_by_columns = []

# Reset the query builder for child template
def reset_child_query_builder():
    st.session_state.parent_template_id = None
    st.session_state.parent_derived_table = None
    st.session_state.parent_columns = []
    st.session_state.selected_columns = []
    st.session_state.aggregations = {}
    st.session_state.group_by_columns = []
    st.session_state.where_conditions = []
    st.session_state.filter_values = {}

# Load template data into the parent query builder
def load_parent_template_data(template_data):
    # Reset current state
    reset_parent_query_builder()
    
    metadata = template_data["metadata"]
    
    # Load selected tables
    st.session_state.selected_tables = metadata["selected_tables"]
    
    # Load table columns
    for table in st.session_state.selected_tables:
        if table not in st.session_state.columns_info:
            st.session_state.columns_info[table] = get_columns(st.session_state.connection, table)
    
    # Load joins
    st.session_state.joins = metadata["joins"]
    
    # Load selected columns
    st.session_state.selected_columns = metadata["selected_columns"]
    
    # Load aggregations
    st.session_state.aggregations = metadata["aggregations"]
    
    # Load group by columns
    st.session_state.group_by_columns = metadata["group_by_columns"]

# Load template data into the child query builder
def load_child_template_data(template_data):
    # Reset current state
    reset_child_query_builder()
    
    metadata = template_data["metadata"]
    
    # Load parent template info
    st.session_state.parent_template_id = metadata["parent_template_id"]
    st.session_state.parent_derived_table = metadata["parent_derived_table"]
    
    # Get parent template to extract parent columns
    parent_template = get_template_by_id(st.session_state.connection, st.session_state.parent_template_id)
    parent_query = parent_template["query"]
    
    # Get columns from parent query
    st.session_state.parent_columns = get_columns_from_query(st.session_state.connection, parent_query)
    
    # Load selected columns
    st.session_state.selected_columns = metadata["selected_columns"]
    
    # Load aggregations
    st.session_state.aggregations = metadata["aggregations"]
    
    # Load group by columns
    st.session_state.group_by_columns = metadata["group_by_columns"]
    
    # Load where conditions
    st.session_state.where_conditions = metadata["where_conditions"]
    
    # Load filter values
    st.session_state.filter_values = metadata.get("filter_values", {})

# Switch to child template mode
def switch_to_child_template_mode(parent_id):
    st.session_state.is_child_template = True
    st.session_state.parent_template_id = parent_id
    
    # Get parent template
    parent_template = get_template_by_id(st.session_state.connection, parent_id)
    parent_query = parent_template["query"]
    
    # Set default derived table name
    st.session_state.parent_derived_table = "PARENT_DATA"
    
    # Get columns from parent query
    st.session_state.parent_columns = get_columns_from_query(st.session_state.connection, parent_query)
    
    # Reset other selections
    st.session_state.selected_columns = []
    st.session_state.aggregations = {}
    st.session_state.group_by_columns = []
    st.session_state.where_conditions = []
    st.session_state.filter_values = {}

# Main application
def main():
    st.title("SQL Template Generator")
    
    # Sidebar for database connection
    with st.sidebar:
        st.header("Database Connection")
        
        username = st.text_input("Username", value="scott", key="username")
        password = st.text_input("Password", value="tiger", type="password", key="password")
        dsn = st.text_input("DSN", value="localhost:1521/XEPDB1", key="dsn")
        
        if st.button("Connect", key="connect_button"):
            connection, message = connect_to_oracle(username, password, dsn)
            if connection:
                st.session_state.connection = connection
                st.session_state.tables = get_tables(connection)
                st.session_state.templates = get_templates(connection)
                st.success(message)
            else:
                st.error(message)
        
        if st.session_state.connection:
            st.success("Connected to Oracle database")
            if st.button("Refresh Tables"):
                st.session_state.tables = get_tables(st.session_state.connection)
            
            if st.button("Refresh Templates"):
                st.session_state.templates = get_templates(st.session_state.connection)
            
            # Template type selector
            st.subheader("Template Type")
            template_type = st.radio(
                "Select template type:",
                ["Parent Template", "Child Template"],
                index=0 if not st.session_state.is_child_template else 1,
                key="template_type_selector"
            )
            
            if template_type == "Parent Template" and st.session_state.is_child_template:
                if st.button("Switch to Parent Template Mode"):
                    st.session_state.is_child_template = False
                    reset_parent_query_builder()
                    st.rerun()
            
            elif template_type == "Child Template" and not st.session_state.is_child_template:
                # Select parent template
                parent_templates = get_parent_templates(st.session_state.templates)
                if not parent_templates:
                    st.warning("No parent templates available. Create a parent template first.")
                else:
                    parent_options = {t["name"]: t["id"] for t in parent_templates}
                    selected_parent = st.selectbox(
                        "Select parent template:",
                        options=list(parent_options.keys()),
                        key="parent_template_selector"
                    )
                    
                    parent_id = parent_options[selected_parent]
                    
                    if st.button("Use This Parent"):
                        switch_to_child_template_mode(parent_id)
                        st.rerun()
    
    # Main content
    if not st.session_state.connection:
        st.info("Please connect to a database first.")
        return
    
    # Create tabs for different actions
    tabs = st.tabs(["View Templates", "Create/Edit Template"])
    
    # Tab for viewing existing templates
    with tabs[0]:
        st.header("Existing SQL Templates")
        
        if not st.session_state.templates:
            st.info("No saved templates found.")
        else:
            # Allow filtering by template type
            template_filter = st.radio(
                "Filter templates:",
                ["All Templates", "Parent Templates", "Child Templates"],
                horizontal=True,
                key="template_filter"
            )
            
            filtered_templates = st.session_state.templates
            if template_filter == "Parent Templates":
                filtered_templates = get_parent_templates(st.session_state.templates)
            elif template_filter == "Child Templates":
                filtered_templates = [t for t in st.session_state.templates if t["parent_id"] is not None]
                
            if not filtered_templates:
                st.info(f"No {template_filter.lower()} found.")
            else:
                template_options = {t["name"]: t["id"] for t in filtered_templates}
                selected_template = st.selectbox(
                    "Select a template to view:", 
                    options=list(template_options.keys()),
                    key="template_selector"
                )
                
                template_id = template_options[selected_template]
                template = next((t for t in filtered_templates if t["id"] == template_id), None)
                
                if template:
                    # Display template type
                    template_type = "Parent Template" if template["parent_id"] is None else "Child Template"
                    st.subheader(f"{template_type}: {template['name']}")
                    
                    # If it's a child template, show the parent
                    if template["parent_id"] is not None:
                        parent = get_template_by_id(st.session_state.connection, template["parent_id"])
                        if parent:
                            st.info(f"Based on parent template: {parent['name']}")
                    
                    # Display SQL Query
                    st.markdown("### SQL Query")
                    st.code(template["query"], language="sql")
                    
                    # Option to edit the template
                    if st.button("Edit this template", key="edit_template_button"):
                        if template["parent_id"] is None:
                            # Load parent template
                            load_parent_template_data(template)
                            st.session_state.is_child_template = False
                        else:
                            # Load child template
                            load_child_template_data(template)
                            st.session_state.is_child_template = True
                        
                        st.session_state.editing_template_id = template["id"]
                        st.session_state.editing_template_name = template["name"]
                        st.rerun()
                    
                    # Option to create a child template from a parent
                    if template["parent_id"] is None:
                        if st.button("Create Child Template From This", key="create_child_button"):
                            switch_to_child_template_mode(template["id"])
                            st.session_state.is_child_template = True
                            st.rerun()
                    
                    # Option to run the query
                    if st.button("Run Query", key="run_query_button"):
                        try:
                            cursor = st.session_state.connection.cursor()
                            cursor.execute(template["query"])
                            columns = [col[0] for col in cursor.description]
                            data = cursor.fetchall()
                            df = pd.DataFrame(data, columns=columns)
                            cursor.close()
                            
                            st.markdown("### Query Results")
                            st.dataframe(df)
                            
                            # Option to download results
                            csv = df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                "Download results as CSV",
                                csv,
                                f"{template['name']}_results.csv",
                                "text/csv",
                                key="download_csv"
                            )
                        except Exception as e:
                            st.error(f"Error executing query: {e}")
                    
                    # Show child templates if this is a parent
                    if template["parent_id"] is None:
                        child_templates = get_child_templates(st.session_state.templates, template["id"])
                        if child_templates:
                            st.markdown("### Child Templates")
                            for child in child_templates:
                                st.write(f"- {child['name']}")
    
    # Tab for creating or editing templates
    with tabs[1]:
        editing_mode = hasattr(st.session_state, 'editing_template_id')
        
        if editing_mode:
            st.header(f"Edit {'Child' if st.session_state.is_child_template else 'Parent'} Template: {st.session_state.editing_template_name}")
            template_name = st.text_input("Template Name", value=st.session_state.editing_template_name, key="edit_template_name")
        else:
            st.header(f"Create New {'Child' if st.session_state.is_child_template else 'Parent'} Template")
            template_name = st.text_input("Template Name", key="new_template_name")
        
        # Different UI based on template type
        if st.session_state.is_child_template:
            # CHILD TEMPLATE CREATION/EDITING
            if not st.session_state.parent_template_id:
                st.error("No parent template selected. Please select a parent template from the sidebar.")
                return
            
            # Show parent template information
            parent_template = get_template_by_id(st.session_state.connection, st.session_state.parent_template_id)
            st.subheader(f"1. Parent Template: {parent_template['name']}")
            
            # Allow setting the alias for the parent query result
            st.session_state.parent_derived_table = st.text_input(
                "Alias for parent query result",
                value=st.session_state.parent_derived_table or "PARENT_DATA",
                key="parent_derived_table_name"
            )
            
            derived_table = st.session_state.parent_derived_table
            
            # Select columns from parent query
            st.subheader("2. Select Columns")
            
            # Display available columns from parent query
            available_columns = [col[0] for col in st.session_state.parent_columns 
                                if col[0] not in st.session_state.selected_columns]
            
            col1, col2 = st.columns(2)
            
            with col1:
                if available_columns:
                    column_to_add = st.selectbox("Available Columns", options=available_columns, key="column_to_add")
                    if st.button("Add Column", key="add_column_button"):
                        st.session_state.selected_columns.append(column_to_add)
                        st.rerun()
                else:
                    st.info("No more columns available")
            
            # Show selected columns and their aggregations
            if st.session_state.selected_columns:
                st.write("Selected Columns and Aggregations:")
                
                for i, col in enumerate(st.session_state.selected_columns):
                    cols = st.columns([3, 2, 1])
                    
                    with cols[0]:
                        st.write(col)
                    
                    with cols[1]:
                        agg_options = ["", "SUM", "AVG", "MIN", "MAX", "COUNT"]
                        current_agg = st.session_state.aggregations.get(col, "")
                        
                        agg_value = st.selectbox(
                            "Aggregation", 
                            options=agg_options,
                            index=agg_options.index(current_agg) if current_agg in agg_options else 0,
                            key=f"agg_{i}"
                        )
                        
                        if agg_value:
                            st.session_state.aggregations[col] = agg_value
                            # If column has aggregation, automatically add to group by all other non-aggregated columns
                            if col not in st.session_state.group_by_columns:
                                for other_col in st.session_state.selected_columns:
                                    if other_col != col and other_col not in st.session_state.aggregations:
                                        if other_col not in st.session_state.group_by_columns:
                                            st.session_state.group_by_columns.append(other_col)
                        elif col in st.session_state.aggregations:
                            del st.session_state.aggregations[col]
                    
                    with cols[2]:
                        if st.button("Remove", key=f"remove_col_{i}"):
                            removed_col = st.session_state.selected_columns.pop(i)
                            if removed_col in st.session_state.aggregations:
                                del st.session_state.aggregations[removed_col]
                            if removed_col in st.session_state.group_by_columns:
                                st.session_state.group_by_columns.remove(removed_col)
                            st.rerun()
            else:
                st.info("No columns selected yet")
            
            # Add WHERE conditions
            st.subheader("3. Where Conditions")
            
            # Display existing conditions
            if st.session_state.where_conditions:
                st.write("Current Filter Conditions:")
                for i, condition in enumerate(st.session_state.where_conditions):
                    cols = st.columns([3, 1, 2, 1])
                    
                    with cols[0]:
                        st.write(condition["column"])
                    
                    with cols[1]:
                        st.write(condition["operator"])
                    
                    with cols[2]:
                        # Display the value or placeholder for the condition
                        if condition["operator"] in ("IS NULL", "IS NOT NULL"):
                            st.write("-")
                        else:
                            col_name = condition["column"]
                            value_key = f"filter_value_{i}"
                            
                            # Get column data type to determine input type
                            col_type = next((c[1] for c in st.session_state.parent_columns 
                                            if c[0] == col_name), "VARCHAR2")
                            
                            # Default value from stored filter values
                            default_value = st.session_state.filter_values.get(col_name, "")
                            
                            # Customize input based on data type
                            if "NUMBER" in col_type:
                                try:
                                    value = st.number_input(
                                        "Value", 
                                        value=float(default_value) if default_value else 0.0,
                                        key=value_key
                                    )
                                except ValueError:
                                    value = st.number_input("Value", value=0.0, key=value_key)
                            elif "DATE" in col_type:
                                value = st.text_input(
                                    "Date (YYYY-MM-DD)", 
                                    value=default_value,
                                    key=value_key
                                )
                            else:  # String type
                                value = st.text_input(
