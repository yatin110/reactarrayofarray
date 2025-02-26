import streamlit as st
import cx_Oracle
import pandas as pd
import json
from datetime import datetime

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

# Save template to database
def save_template(connection, template_name, sql_query, metadata):
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
                    created_date DATE DEFAULT SYSDATE,
                    modified_date DATE DEFAULT SYSDATE
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
                    modified_date = SYSDATE
                WHERE template_id = :id
            """, query=sql_query, metadata=metadata, id=template_id)
            message = f"Template '{template_name}' updated successfully!"
        else:
            # Insert new template
            cursor.execute("""
                INSERT INTO SQL_TEMPLATES (template_name, sql_query, metadata)
                VALUES (:name, :query, :metadata)
            """, name=template_name, query=sql_query, metadata=metadata)
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
            SELECT template_id, template_name, sql_query, metadata
            FROM SQL_TEMPLATES
            ORDER BY template_name
        """)
        templates = [
            {
                "id": row[0], 
                "name": row[1], 
                "query": row[2], 
                "metadata": json.loads(row[3])
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
            SELECT template_id, template_name, sql_query, metadata
            FROM SQL_TEMPLATES
            WHERE template_id = :id
        """, id=template_id)
        
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0], 
                "name": row[1], 
                "query": row[2], 
                "metadata": json.loads(row[3])
            }
        return None
    except Exception as e:
        st.error(f"Error fetching template: {e}")
        return None
    finally:
        cursor.close()

# Generate SQL query based on user selections
def generate_sql_query():
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

# Reset the query builder
def reset_query_builder():
    st.session_state.selected_tables = []
    st.session_state.joins = []
    st.session_state.selected_columns = []
    st.session_state.aggregations = {}
    st.session_state.group_by_columns = []

# Load template data into the query builder
def load_template_data(template_data):
    # Reset current state
    reset_query_builder()
    
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
            template_options = {t["name"]: t["id"] for t in st.session_state.templates}
            selected_template = st.selectbox(
                "Select a template to view:", 
                options=list(template_options.keys()),
                key="template_selector"
            )
            
            template_id = template_options[selected_template]
            template = next((t for t in st.session_state.templates if t["id"] == template_id), None)
            
            if template:
                st.subheader(f"Template: {template['name']}")
                
                # Display SQL Query
                st.markdown("### SQL Query")
                st.code(template["query"], language="sql")
                
                # Option to edit the template
                if st.button("Edit this template", key="edit_template_button"):
                    load_template_data(template)
                    st.session_state.editing_template_id = template["id"]
                    st.session_state.editing_template_name = template["name"]
                    st.session_state.tab_index = 1  # Switch to Create/Edit tab
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
    
    # Tab for creating or editing templates
    with tabs[1]:
        editing_mode = hasattr(st.session_state, 'editing_template_id')
        
        if editing_mode:
            st.header(f"Edit Template: {st.session_state.editing_template_name}")
            template_name = st.text_input("Template Name", value=st.session_state.editing_template_name, key="edit_template_name")
        else:
            st.header("Create New SQL Template")
            template_name = st.text_input("Template Name", key="new_template_name")
        
        # Select tables
        st.subheader("1. Select Tables")
        available_tables = [t for t in st.session_state.tables if t not in st.session_state.selected_tables]
        
        col1, col2 = st.columns(2)
        
        with col1:
            if available_tables:
                table_to_add = st.selectbox("Available Tables", options=available_tables, key="table_to_add")
                if st.button("Add Table", key="add_table_button"):
                    st.session_state.selected_tables.append(table_to_add)
                    # Get columns for the newly added table
                    st.session_state.columns_info[table_to_add] = get_columns(st.session_state.connection, table_to_add)
                    st.rerun()
            else:
                st.info("No more tables available")
        
        with col2:
            if st.session_state.selected_tables:
                st.write("Selected Tables:")
                for i, table in enumerate(st.session_state.selected_tables):
                    cols = st.columns([4, 1])
                    with cols[0]:
                        st.write(f"{i+1}. {table}")
                    with cols[1]:
                        if st.button("Remove", key=f"remove_table_{i}"):
                            # Remove this table
                            removed_table = st.session_state.selected_tables.pop(i)
                            
                            # Remove any columns from this table
                            st.session_state.selected_columns = [
                                col for col in st.session_state.selected_columns 
                                if not col.startswith(f"{removed_table}.")
                            ]
                            
                            # Remove any joins involving this table
                            st.session_state.joins = [
                                join for join in st.session_state.joins
                                if not (join["source"].startswith(f"{removed_table}.") or 
                                        join["target"].startswith(f"{removed_table}."))
                            ]
                            
                            # Remove from group by
                            st.session_state.group_by_columns = [
                                col for col in st.session_state.group_by_columns
                                if not col.startswith(f"{removed_table}.")
                            ]
                            
                            # Remove aggregations
                            keys_to_remove = [
                                key for key in st.session_state.aggregations.keys()
                                if key.startswith(f"{removed_table}.")
                            ]
                            for key in keys_to_remove:
                                del st.session_state.aggregations[key]
                                
                            st.rerun()
            else:
                st.info("No tables selected yet")
        
        # Create joins between tables
        if len(st.session_state.selected_tables) > 1:
            st.subheader("2. Create Joins")
            
            # Collect all columns from all selected tables
            all_columns = {}
            for table in st.session_state.selected_tables:
                if table in st.session_state.columns_info:
                    all_columns[table] = [f"{table}.{col[0]}" for col in st.session_state.columns_info[table]]
            
            # Display existing joins
            if st.session_state.joins:
                st.write("Existing Joins:")
                for i, join in enumerate(st.session_state.joins):
                    cols = st.columns([4, 1])
                    with cols[0]:
                        st.write(f"{i+1}. {join['source']} = {join['target']}")
                    with cols[1]:
                        if st.button("Remove", key=f"remove_join_{i}"):
                            st.session_state.joins.pop(i)
                            st.rerun()
            
            # Add new join
            st.write("Add New Join:")
            col1, col2, col3 = st.columns([3, 1, 3])
            
            with col1:
                source_options = []
                for table in st.session_state.selected_tables:
                    if table in st.session_state.columns_info:
                        for col in st.session_state.columns_info[table]:
                            source_options.append(f"{table}.{col[0]}")
                
                source_column = st.selectbox("Source Column", options=source_options, key="source_column")
            
            with col2:
                st.write("=")
            
            with col3:
                target_options = []
                if source_column:
                    source_table = source_column.split(".")[0]
                    for table in st.session_state.selected_tables:
                        if table != source_table and table in st.session_state.columns_info:
                            for col in st.session_state.columns_info[table]:
                                target_options.append(f"{table}.{col[0]}")
                
                target_column = st.selectbox("Target Column", options=target_options, key="target_column")
            
            if source_column and target_column and st.button("Add Join", key="add_join_button"):
                # Check if this join already exists
                join_exists = any(
                    (join["source"] == source_column and join["target"] == target_column) or
                    (join["source"] == target_column and join["target"] == source_column)
                    for join in st.session_state.joins
                )
                
                if not join_exists:
                    st.session_state.joins.append({
                        "source": source_column,
                        "target": target_column
                    })
                    st.rerun()
                else:
                    st.warning("This join already exists.")
        
        # Select columns and set aggregations
        if st.session_state.selected_tables:
            st.subheader("3. Select Columns and Aggregations")
            
            # Display all columns from selected tables
            all_columns = []
            for table in st.session_state.selected_tables:
                if table in st.session_state.columns_info:
                    for col in st.session_state.columns_info[table]:
                        all_columns.append(f"{table}.{col[0]}")
            
            # Available columns (not yet selected)
            available_columns = [col for col in all_columns if col not in st.session_state.selected_columns]
            
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
        
        # Group by settings
        if st.session_state.aggregations and st.session_state.selected_columns:
            st.subheader("4. Group By Columns")
            
            # Get non-aggregated columns
            non_agg_columns = [
                col for col in st.session_state.selected_columns
                if col not in st.session_state.aggregations or not st.session_state.aggregations[col]
            ]
            
            # Display current group by columns
            if st.session_state.group_by_columns:
                st.write("Current Group By Columns:")
                for i, col in enumerate(st.session_state.group_by_columns):
                    cols = st.columns([4, 1])
                    with cols[0]:
                        st.write(f"{i+1}. {col}")
                    with cols[1]:
                        if st.button("Remove", key=f"remove_group_{i}"):
                            st.session_state.group_by_columns.remove(col)
                            st.rerun()
            
            # Add columns to group by
            available_for_group_by = [
                col for col in non_agg_columns
                if col not in st.session_state.group_by_columns
            ]
            
            if available_for_group_by:
                col_to_group = st.selectbox(
                    "Add Column to Group By", 
                    options=available_for_group_by,
                    key="group_by_column"
                )
                
                if st.button("Add to Group By", key="add_group_by"):
                    st.session_state.group_by_columns.append(col_to_group)
                    st.rerun()
        
        # Generate SQL Query
        if st.session_state.selected_columns:
            st.subheader("5. Generated SQL Query")
            
            sql_query = generate_sql_query()
            st.code(sql_query, language="sql")
            
            # Save template option
            if template_name.strip():
                # Prepare metadata for saving
                metadata = {
                    "selected_tables": st.session_state.selected_tables,
                    "joins": st.session_state.joins,
                    "selected_columns": st.session_state.selected_columns,
                    "aggregations": st.session_state.aggregations,
                    "group_by_columns": st.session_state.group_by_columns
                }
                
                metadata_json = json.dumps(metadata)
                
                if st.button("Save Template", key="save_template_button"):
                    success, message = save_template(
                        st.session_state.connection,
                        template_name,
                        sql_query,
                        metadata_json
                    )
                    
                    if success:
                        st.success(message)
                        st.session_state.templates = get_templates(st.session_state.connection)
                        
                        # Clear editing state if we were editing
                        if hasattr(st.session_state, 'editing_template_id'):
                            delattr(st.session_state, 'editing_template_id')
                            delattr(st.session_state, 'editing_template_name')
                            
                        # Reset the form for a new template
                        reset_query_builder()
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.warning("Please enter a template name before saving.")
        
        # Reset button
        if st.button("Reset Form", key="reset_form"):
            reset_query_builder()
            if hasattr(st.session_state, 'editing_template_id'):
                delattr(st.session_state, 'editing_template_id')
                delattr(st.session_state, 'editing_template_name')
            st.rerun()

if __name__ == "__main__":
    main()
