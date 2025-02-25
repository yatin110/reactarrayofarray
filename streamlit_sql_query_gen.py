import streamlit as st
import cx_Oracle
import pandas as pd
from sqlalchemy import create_engine
import json

# Set page config
st.set_page_config(page_title="SQL Template Manager", layout="wide")

# Database connection parameters - would be stored securely in practice
DB_CONFIG = {
    "user": "your_username",
    "password": "your_password",
    "dsn": "your_dsn",  # format: hostname:port/service_name
}

# Initialize session state variables if they don't exist
if 'tables' not in st.session_state:
    st.session_state.tables = []
if 'selected_tables' not in st.session_state:
    st.session_state.selected_tables = []
if 'joins' not in st.session_state:
    st.session_state.joins = []
if 'conditions' not in st.session_state:
    st.session_state.conditions = []
if 'group_by' not in st.session_state:
    st.session_state.group_by = []
if 'order_by' not in st.session_state:
    st.session_state.order_by = []
if 'selected_columns' not in st.session_state:
    st.session_state.selected_columns = []
if 'editing_template_id' not in st.session_state:
    st.session_state.editing_template_id = None
if 'template_name' not in st.session_state:
    st.session_state.template_name = ""
if 'template_description' not in st.session_state:
    st.session_state.template_description = ""

def get_db_connection():
    """Establish connection to Oracle database"""
    try:
        connection = cx_Oracle.connect(
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            dsn=DB_CONFIG["dsn"]
        )
        return connection
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

def get_sqlalchemy_engine():
    """Create SQLAlchemy engine for Oracle connection"""
    connection_string = f"oracle+cx_oracle://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['dsn']}"
    return create_engine(connection_string)

def get_all_tables():
    """Get all tables from the Oracle database"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT table_name 
                FROM user_tables 
                ORDER BY table_name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return tables
        except Exception as e:
            st.error(f"Error fetching tables: {e}")
            return []
    return []

def get_table_columns(table_name):
    """Get columns for a specific table"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT column_name, data_type
                FROM user_tab_columns
                WHERE table_name = '{table_name}'
                ORDER BY column_id
            """)
            columns = [(row[0], row[1]) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return columns
        except Exception as e:
            st.error(f"Error fetching columns for {table_name}: {e}")
            return []
    return []

def get_saved_templates():
    """Get all saved SQL templates"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # Check if SQL_TEMPLATES table exists, if not create it
            cursor.execute("""
                SELECT COUNT(*) FROM user_tables WHERE table_name = 'SQL_TEMPLATES'
            """)
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    CREATE TABLE SQL_TEMPLATES (
                        id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        name VARCHAR2(100) NOT NULL,
                        description VARCHAR2(1000),
                        query CLOB,
                        template_data CLOB,
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        modified_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                
            cursor.execute("""
                SELECT id, name, description, query
                FROM SQL_TEMPLATES
                ORDER BY modified_date DESC
            """)
            templates = [
                {"id": row[0], "name": row[1], "description": row[2], "query": row[3]}
                for row in cursor.fetchall()
            ]
            cursor.close()
            conn.close()
            return templates
        except Exception as e:
            st.error(f"Error fetching templates: {e}")
            return []
    return []

def save_template(name, description, query, template_data):
    """Save a new SQL template"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO SQL_TEMPLATES (name, description, query, template_data)
                VALUES (:1, :2, :3, :4)
            """, (name, description, query, template_data))
            conn.commit()
            cursor.close()
            conn.close()
            st.success("Template saved successfully!")
            return True
        except Exception as e:
            st.error(f"Error saving template: {e}")
            return False
    return False

def update_template(template_id, name, description, query, template_data):
    """Update an existing SQL template"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE SQL_TEMPLATES
                SET name = :1, description = :2, query = :3, template_data = :4, modified_date = CURRENT_TIMESTAMP
                WHERE id = :5
            """, (name, description, query, template_data, template_id))
            conn.commit()
            cursor.close()
            conn.close()
            st.success("Template updated successfully!")
            return True
        except Exception as e:
            st.error(f"Error updating template: {e}")
            return False
    return False

def get_template_by_id(template_id):
    """Get a template by ID"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, description, query, template_data
                FROM SQL_TEMPLATES
                WHERE id = :1
            """, (template_id,))
            row = cursor.fetchone()
            if row:
                template = {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "query": row[3],
                    "template_data": row[4]
                }
                cursor.close()
                conn.close()
                return template
            cursor.close()
            conn.close()
            return None
        except Exception as e:
            st.error(f"Error fetching template: {e}")
            return None
    return None

def load_template(template_data):
    """Load template data into session state"""
    data = json.loads(template_data)
    st.session_state.selected_tables = data.get("selected_tables", [])
    st.session_state.joins = data.get("joins", [])
    st.session_state.conditions = data.get("conditions", [])
    st.session_state.group_by = data.get("group_by", [])
    st.session_state.order_by = data.get("order_by", [])
    st.session_state.selected_columns = data.get("selected_columns", [])
    st.session_state.template_name = data.get("name", "")
    st.session_state.template_description = data.get("description", "")

def generate_sql_query():
    """Generate SQL query based on user selections"""
    if not st.session_state.selected_tables:
        return "-- Please select at least one table"
    
    # SELECT clause
    selected_columns = st.session_state.selected_columns
    if not selected_columns:
        select_clause = "SELECT *"
    else:
        select_clause = "SELECT " + ", ".join(selected_columns)
    
    # FROM clause
    from_clause = f"FROM {st.session_state.selected_tables[0]}"
    
    # JOIN clause
    join_clause = ""
    for join in st.session_state.joins:
        join_clause += f"\n{join['type']} JOIN {join['table']} ON {join['left_column']} = {join['right_column']}"
    
    # WHERE clause
    where_clause = ""
    if st.session_state.conditions:
        conditions = []
        for condition in st.session_state.conditions:
            cond_str = f"{condition['column']} {condition['operator']} "
            if condition['operator'].upper() in ('LIKE', '=', '<>', '>', '<', '>=', '<='):
                if condition['operator'].upper() == 'LIKE':
                    cond_str += f"'%{condition['value']}%'"
                else:
                    cond_str += f"'{condition['value']}'"
            else:
                cond_str += condition['value']
            conditions.append(cond_str)
        where_clause = "\nWHERE " + " AND ".join(conditions)
    
    # GROUP BY clause
    group_by_clause = ""
    if st.session_state.group_by:
        group_by_clause = "\nGROUP BY " + ", ".join(st.session_state.group_by)
    
    # ORDER BY clause
    order_by_clause = ""
    if st.session_state.order_by:
        order_items = []
        for order in st.session_state.order_by:
            order_items.append(f"{order['column']} {order['direction']}")
        order_by_clause = "\nORDER BY " + ", ".join(order_items)
    
    # Combine all clauses
    query = f"{select_clause}\n{from_clause}{join_clause}{where_clause}{group_by_clause}{order_by_clause}"
    return query

def reset_session_state():
    """Reset all session state variables"""
    st.session_state.selected_tables = []
    st.session_state.joins = []
    st.session_state.conditions = []
    st.session_state.group_by = []
    st.session_state.order_by = []
    st.session_state.selected_columns = []
    st.session_state.editing_template_id = None
    st.session_state.template_name = ""
    st.session_state.template_description = ""

def preview_query_results(query):
    """Execute the query and preview results"""
    try:
        engine = get_sqlalchemy_engine()
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        st.error(f"Error executing query: {e}")
        return None

def main():
    st.title("SQL Template Manager")
    
    # Navigation menu
    menu = ["View Templates", "Create Template", "Edit Template"]
    choice = st.sidebar.selectbox("Menu", menu)
    
    # Load tables
    if not st.session_state.tables:
        st.session_state.tables = get_all_tables()
    
    if choice == "View Templates":
        st.header("Saved SQL Templates")
        templates = get_saved_templates()
        
        if not templates:
            st.info("No templates found. Create a new template to get started.")
        else:
            template_names = [f"{t['name']} (ID: {t['id']})" for t in templates]
            selected_template_name = st.selectbox("Select a template", template_names)
            
            if selected_template_name:
                template_id = int(selected_template_name.split("(ID: ")[1].split(")")[0])
                template = next((t for t in templates if t["id"] == template_id), None)
                
                if template:
                    st.subheader(template["name"])
                    st.write(template["description"])
                    
                    st.code(template["query"], language="sql")
                    
                    # Buttons for actions
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("Execute Query"):
                            df = preview_query_results(template["query"])
                            if df is not None:
                                st.dataframe(df)
                    
                    with col2:
                        if st.button("Edit Template"):
                            st.session_state.editing_template_id = template_id
                            st.experimental_rerun()
                    
                    with col3:
                        if st.button("Copy to Clipboard"):
                            st.success("Query copied to clipboard!")
    
    elif choice == "Create Template" or choice == "Edit Template":
        is_editing = choice == "Edit Template"
        
        if is_editing:
            if st.session_state.editing_template_id is None:
                templates = get_saved_templates()
                if not templates:
                    st.info("No templates available to edit. Create a new template first.")
                    return
                
                template_names = [f"{t['name']} (ID: {t['id']})" for t in templates]
                selected_template_name = st.selectbox("Select a template to edit", template_names)
                
                if selected_template_name:
                    template_id = int(selected_template_name.split("(ID: ")[1].split(")")[0])
                    st.session_state.editing_template_id = template_id
                    template = get_template_by_id(template_id)
                    
                    if template and template.get("template_data"):
                        load_template(template["template_data"])
                    
                    st.button("Load Template Data", on_click=lambda: None)
            else:
                st.header(f"Editing Template (ID: {st.session_state.editing_template_id})")
                if st.button("Cancel Editing"):
                    reset_session_state()
                    st.experimental_rerun()
        else:
            st.header("Create SQL Template")
        
        # Template details
        with st.expander("Template Details", expanded=True):
            st.session_state.template_name = st.text_input("Template Name", value=st.session_state.template_name)
            st.session_state.template_description = st.text_area("Description", value=st.session_state.template_description)
        
        # Table selection
        with st.expander("Select Tables", expanded=True):
            available_tables = st.session_state.tables
            
            if not st.session_state.selected_tables:
                # Select the main table
                main_table = st.selectbox("Select Main Table", available_tables)
                if st.button("Add Main Table"):
                    st.session_state.selected_tables.append(main_table)
                    st.experimental_rerun()
            else:
                # Show selected tables
                st.write("Selected Tables:")
                for i, table in enumerate(st.session_state.selected_tables):
                    st.write(f"{i+1}. {table}")
                
                # Option to add more tables for joins
                remaining_tables = [t for t in available_tables if t not in st.session_state.selected_tables]
                if remaining_tables:
                    new_table = st.selectbox("Add Another Table", remaining_tables)
                    if st.button("Add Table"):
                        st.session_state.selected_tables.append(new_table)
                        st.experimental_rerun()
        
        # Column selection
        if st.session_state.selected_tables:
            with st.expander("Select Columns", expanded=True):
                all_columns = []
                column_options = []
                
                for table in st.session_state.selected_tables:
                    table_columns = get_table_columns(table)
                    for col_name, col_type in table_columns:
                        column_full_name = f"{table}.{col_name}"
                        all_columns.append((column_full_name, col_type))
                        column_options.append(column_full_name)
                
                # Select columns for the query
                st.write("Select columns to include in the query:")
                
                # Option to select all columns
                if st.checkbox("Select All Columns", value=len(st.session_state.selected_columns) == len(column_options) or len(st.session_state.selected_columns) == 0):
                    st.session_state.selected_columns = []  # Empty means all columns (*)
                else:
                    selected = st.multiselect(
                        "Choose Columns", 
                        column_options,
                        default=st.session_state.selected_columns
                    )
                    
                    if st.button("Update Selected Columns"):
                        st.session_state.selected_columns = selected
                        st.experimental_rerun()
        
            # Joins
            if len(st.session_state.selected_tables) > 1:
                with st.expander("Define Joins", expanded=True):
                    st.write("Create Joins Between Tables:")
                    
                    # Show existing joins
                    if st.session_state.joins:
                        st.write("Current Joins:")
                        for i, join in enumerate(st.session_state.joins):
                            st.write(f"{i+1}. {join['left_column']} {join['type']} {join['right_column']}")
                        
                        if st.button("Remove All Joins"):
                            st.session_state.joins = []
                            st.experimental_rerun()
                    
                    # Add new join
                    join_types = ["INNER", "LEFT", "RIGHT", "FULL"]
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        left_table = st.selectbox("Left Table", st.session_state.selected_tables, key="join_left_table")
                        left_columns = [f"{left_table}.{col[0]}" for col in get_table_columns(left_table)]
                        left_column = st.selectbox("Left Column", left_columns, key="join_left_column")
                    
                    with col2:
                        join_type = st.selectbox("Join Type", join_types, key="join_type")
                    
                    with col3:
                        right_table = st.selectbox("Right Table", 
                                                  [t for t in st.session_state.selected_tables if t != left_table], 
                                                  key="join_right_table")
                        right_columns = [f"{right_table}.{col[0]}" for col in get_table_columns(right_table)]
                        right_column = st.selectbox("Right Column", right_columns, key="join_right_column")
                    
                    if st.button("Add Join"):
                        st.session_state.joins.append({
                            "table": right_table,
                            "type": join_type,
                            "left_column": left_column,
                            "right_column": right_column
                        })
                        st.experimental_rerun()
            
            # WHERE conditions
            with st.expander("WHERE Conditions", expanded=True):
                st.write("Add Filter Conditions:")
                
                # Show existing conditions
                if st.session_state.conditions:
                    st.write("Current Conditions:")
                    for i, condition in enumerate(st.session_state.conditions):
                        st.write(f"{i+1}. {condition['column']} {condition['operator']} {condition['value']}")
                    
                    if st.button("Remove All Conditions"):
                        st.session_state.conditions = []
                        st.experimental_rerun()
                
                # Add new condition
                column_options = []
                for table in st.session_state.selected_tables:
                    table_columns = get_table_columns(table)
                    for col_name, _ in table_columns:
                        column_options.append(f"{table}.{col_name}")
                
                operators = ["=", "<>", ">", "<", ">=", "<=", "LIKE", "IN", "NOT IN", "IS NULL", "IS NOT NULL"]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    condition_column = st.selectbox("Column", column_options, key="cond_column")
                
                with col2:
                    condition_operator = st.selectbox("Operator", operators, key="cond_operator")
                
                with col3:
                    condition_value = ""
                    if condition_operator not in ["IS NULL", "IS NOT NULL"]:
                        condition_value = st.text_input("Value", key="cond_value")
                
                if st.button("Add Condition"):
                    st.session_state.conditions.append({
                        "column": condition_column,
                        "operator": condition_operator,
                        "value": condition_value
                    })
                    st.experimental_rerun()
            
            # GROUP BY
            with st.expander("GROUP BY", expanded=True):
                st.write("Add GROUP BY Columns:")
                
                column_options = []
                for table in st.session_state.selected_tables:
                    table_columns = get_table_columns(table)
                    for col_name, _ in table_columns:
                        column_options.append(f"{table}.{col_name}")
                
                selected_group_by = st.multiselect(
                    "Select columns for GROUP BY", 
                    column_options,
                    default=st.session_state.group_by
                )
                
                if st.button("Update GROUP BY"):
                    st.session_state.group_by = selected_group_by
                    st.experimental_rerun()
            
            # ORDER BY
            with st.expander("ORDER BY", expanded=True):
                st.write("Add ORDER BY Columns:")
                
                # Show existing order by
                if st.session_state.order_by:
                    st.write("Current ORDER BY:")
                    for i, order in enumerate(st.session_state.order_by):
                        st.write(f"{i+1}. {order['column']} {order['direction']}")
                    
                    if st.button("Remove All ORDER BY"):
                        st.session_state.order_by = []
                        st.experimental_rerun()
                
                # Add new order by
                column_options = []
                for table in st.session_state.selected_tables:
                    table_columns = get_table_columns(table)
                    for col_name, _ in table_columns:
                        column_options.append(f"{table}.{col_name}")
                
                col1, col2 = st.columns(2)
                with col1:
                    order_column = st.selectbox("Column", column_options, key="order_column")
                
                with col2:
                    order_direction = st.selectbox("Direction", ["ASC", "DESC"], key="order_direction")
                
                if st.button("Add ORDER BY"):
                    st.session_state.order_by.append({
                        "column": order_column,
                        "direction": order_direction
                    })
                    st.experimental_rerun()
            
            # Generate SQL query
            st.subheader("Generated SQL Query")
            query = generate_sql_query()
            st.code(query, language="sql")
            
            # Preview results
            if st.button("Preview Results"):
                if st.session_state.selected_tables:
                    df = preview_query_results(query)
                    if df is not None:
                        st.dataframe(df)
            
            # Save template
            st.subheader("Save Template")
            if not st.session_state.template_name:
                st.warning("Please enter a template name before saving.")
            else:
                template_data = {
                    "name": st.session_state.template_name,
                    "description": st.session_state.template_description,
                    "selected_tables": st.session_state.selected_tables,
                    "joins": st.session_state.joins,
                    "conditions": st.session_state.conditions,
                    "group_by": st.session_state.group_by,
                    "order_by": st.session_state.order_by,
                    "selected_columns": st.session_state.selected_columns
                }
                
                if is_editing and st.session_state.editing_template_id is not None:
                    if st.button("Update Template"):
                        success = update_template(
                            st.session_state.editing_template_id,
                            st.session_state.template_name,
                            st.session_state.template_description,
                            query,
                            json.dumps(template_data)
                        )
                        if success:
                            reset_session_state()
                            st.experimental_rerun()
                else:
                    if st.button("Save as New Template"):
                        success = save_template(
                            st.session_state.template_name,
                            st.session_state.template_description,
                            query,
                            json.dumps(template_data)
                        )
                        if success:
                            reset_session_state()
                            st.experimental_rerun()

if __name__ == "__main__":
    main()
