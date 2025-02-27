import streamlit as st
import cx_Oracle
import pandas as pd
from sqlalchemy import create_engine
import re
import json

def init_connection():
    try:
        conn_info = st.session_state.get('conn_info', {})
        if not conn_info:
            return None
            
        username = conn_info.get('username')
        password = conn_info.get('password')
        host = conn_info.get('host')
        port = conn_info.get('port')
        service_name = conn_info.get('service_name')
        
        dsn = cx_Oracle.makedsn(host, port, service_name=service_name)
        conn = cx_Oracle.connect(username, password, dsn)
        return conn
    except Exception as e:
        st.error(f"Error connecting to database: {str(e)}")
        return None

def get_engine():
    try:
        conn_info = st.session_state.get('conn_info', {})
        if not conn_info:
            return None
            
        username = conn_info.get('username')
        password = conn_info.get('password')
        host = conn_info.get('host')
        port = conn_info.get('port')
        service_name = conn_info.get('service_name')
        
        connection_string = f"oracle+cx_oracle://{username}:{password}@{host}:{port}/?service_name={service_name}"
        engine = create_engine(connection_string)
        return engine
    except Exception as e:
        st.error(f"Error creating SQLAlchemy engine: {str(e)}")
        return None

def get_all_tables():
    conn = init_connection()
    if not conn:
        return []
    
    cursor = conn.cursor()
    cursor.execute("SELECT owner, table_name FROM all_tables WHERE owner = USER ORDER BY table_name")
    tables = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return [f"{row[0]}.{row[1]}" for row in tables]

def get_table_columns(table_name):
    if '.' in table_name:
        schema, table = table_name.split('.')
    else:
        schema = None
        table = table_name
        
    conn = init_connection()
    if not conn:
        return []
    
    cursor = conn.cursor()
    
    if schema:
        cursor.execute("""
            SELECT column_name, data_type
            FROM all_tab_columns
            WHERE owner = :schema AND table_name = :table
            ORDER BY column_id
        """, schema=schema, table=table)
    else:
        cursor.execute("""
            SELECT column_name, data_type
            FROM all_tab_columns
            WHERE owner = USER AND table_name = :table
            ORDER BY column_id
        """, table=table)
        
    columns = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return [(col[0], col[1]) for col in columns]

def get_templates():
    conn = init_connection()
    if not conn:
        return []
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT template_id, template_name, template_type, parent_template_id
            FROM SQL_TEMPLATES
            ORDER BY template_name
        """)
        templates = cursor.fetchall()
        return [(row[0], row[1], row[2], row[3]) for row in templates]
    except:
        create_template_tables()
        return []
    finally:
        cursor.close()
        conn.close()

def create_template_tables():
    conn = init_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            BEGIN
                EXECUTE IMMEDIATE 'CREATE TABLE SQL_TEMPLATES (
                    template_id NUMBER PRIMARY KEY,
                    template_name VARCHAR2(200) NOT NULL,
                    template_type VARCHAR2(20) NOT NULL,
                    parent_template_id NUMBER,
                    sql_query CLOB,
                    template_data CLOB,
                    created_date DATE DEFAULT SYSDATE,
                    modified_date DATE DEFAULT SYSDATE,
                    CONSTRAINT fk_parent_template FOREIGN KEY (parent_template_id) 
                    REFERENCES SQL_TEMPLATES(template_id)
                )';
                
                EXECUTE IMMEDIATE 'CREATE SEQUENCE template_id_seq START WITH 1 INCREMENT BY 1';
                
                EXECUTE IMMEDIATE 'CREATE OR REPLACE TRIGGER template_id_trigger
                    BEFORE INSERT ON SQL_TEMPLATES
                    FOR EACH ROW
                    BEGIN
                        IF :NEW.template_id IS NULL THEN
                            SELECT template_id_seq.NEXTVAL INTO :NEW.template_id FROM DUAL;
                        END IF;
                    END;';
            EXCEPTION
                WHEN OTHERS THEN
                    IF SQLCODE = -955 THEN
                        NULL;
                    ELSE
                        RAISE;
                    END IF;
            END;
        """)
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error creating template tables: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

def save_template(template_name, template_type, parent_template_id, sql_query, template_data):
    conn = init_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO SQL_TEMPLATES (
                template_name, template_type, parent_template_id, sql_query, template_data
            ) VALUES (
                :template_name, :template_type, :parent_template_id, :sql_query, :template_data
            )
        """, 
        template_name=template_name,
        template_type=template_type,
        parent_template_id=parent_template_id if parent_template_id else None,
        sql_query=sql_query,
        template_data=template_data
        )
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error saving template: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

def update_template(template_id, template_name, sql_query, template_data):
    conn = init_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE SQL_TEMPLATES
            SET template_name = :template_name,
                sql_query = :sql_query,
                template_data = :template_data,
                modified_date = SYSDATE
            WHERE template_id = :template_id
        """, 
        template_id=template_id,
        template_name=template_name,
        sql_query=sql_query,
        template_data=template_data
        )
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error updating template: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_template_details(template_id):
    conn = init_connection()
    if not conn:
        return None
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT template_id, template_name, template_type, parent_template_id, sql_query, template_data
            FROM SQL_TEMPLATES
            WHERE template_id = :template_id
        """, template_id=template_id)
        
        template = cursor.fetchone()
        if template:
            return {
                'template_id': template[0],
                'template_name': template[1],
                'template_type': template[2],
                'parent_template_id': template[3],
                'sql_query': template[4].read() if template[4] else '',
                'template_data': template[5].read() if template[5] else '{}'
            }
        return None
    except Exception as e:
        st.error(f"Error getting template details: {str(e)}")
        return None
    finally:
        cursor.close()
        conn.close()

def execute_query(query):
    try:
        engine = get_engine()
        if not engine:
            return None
        
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        st.error(f"Error executing query: {str(e)}")
        return None

def generate_sql_from_template(template_data):
    data = json.loads(template_data)
    
    selected_tables = data.get('selected_tables', [])
    selected_columns = data.get('selected_columns', [])
    join_conditions = data.get('join_conditions', [])
    aggregations = data.get('aggregations', {})
    group_by_columns = data.get('group_by_columns', [])
    
    if not selected_tables:
        return "-- Please select at least one table"
    
    if not selected_columns:
        return "-- Please select at least one column"
    
    # Build the SELECT part
    select_parts = []
    for col in selected_columns:
        if col in aggregations and aggregations[col]:
            agg_type = aggregations[col]
            select_parts.append(f"{agg_type}({col}) AS {col.split('.')[-1]}_{agg_type.lower()}")
        else:
            select_parts.append(col)
    
    select_clause = ",\n    ".join(select_parts)
    
    # Build the FROM part
    from_clause = selected_tables[0]
    
    # Build the JOIN part
    join_clause = ""
    for join in join_conditions:
        left_table = join.get('left_table')
        left_column = join.get('left_column')
        right_table = join.get('right_table')
        right_column = join.get('right_column')
        join_type = join.get('join_type', 'INNER JOIN')
        
        join_clause += f"\n{join_type} {right_table} ON {left_table}.{left_column} = {right_table}.{right_column}"
    
    # Build the GROUP BY part
    group_by_clause = ""
    if group_by_columns:
        group_by_clause = "\nGROUP BY " + ",\n    ".join(group_by_columns)
    
    # Combine all parts
    sql = f"SELECT\n    {select_clause}\nFROM {from_clause}{join_clause}{group_by_clause}"
    
    return sql

def login_form():
    with st.form("login_form"):
        st.subheader("Database Connection")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        host = st.text_input("Host", value="localhost")
        port = st.text_input("Port", value="1521")
        service_name = st.text_input("Service Name")
        
        submit = st.form_submit_button("Connect")
        
        if submit:
            conn_info = {
                'username': username,
                'password': password,
                'host': host,
                'port': port,
                'service_name': service_name
            }
            st.session_state['conn_info'] = conn_info
            
            conn = init_connection()
            if conn:
                st.session_state['connected'] = True
                st.success("Connected to Oracle database successfully!")
                conn.close()
            else:
                st.error("Failed to connect to Oracle database!")

def parent_template_creation():
    st.subheader("Create Parent SQL Template")
    
    template_name = st.text_input("Template Name")
    
    tables = get_all_tables()
    selected_tables = st.multiselect("Select Tables", tables)
    
    # Store selected tables
    if 'selected_tables' not in st.session_state:
        st.session_state['selected_tables'] = []
    
    if selected_tables:
        st.session_state['selected_tables'] = selected_tables
    
    # Get columns for each selected table
    all_columns = []
    table_columns = {}
    
    for table in st.session_state['selected_tables']:
        columns = get_table_columns(table)
        table_columns[table] = columns
        all_columns.extend([f"{table}.{col[0]}" for col in columns])
    
    # Select columns
    selected_columns = st.multiselect("Select Columns", all_columns)
    
    # Set up join conditions if multiple tables are selected
    join_conditions = []
    
    if len(st.session_state['selected_tables']) > 1:
        st.subheader("Join Conditions")
        
        for i in range(len(st.session_state['selected_tables']) - 1):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                left_table = st.selectbox(f"Left Table #{i+1}", st.session_state['selected_tables'], key=f"left_table_{i}")
                left_columns = [col[0] for col in table_columns.get(left_table, [])]
                left_column = st.selectbox(f"Left Column #{i+1}", left_columns, key=f"left_column_{i}")
            
            with col2:
                join_type = st.selectbox(f"Join Type #{i+1}", 
                                        ["INNER JOIN", "LEFT OUTER JOIN", "RIGHT OUTER JOIN", "FULL OUTER JOIN"], 
                                        key=f"join_type_{i}")
            
            with col3:
                remaining_tables = [t for t in st.session_state['selected_tables'] if t != left_table]
                right_table = st.selectbox(f"Right Table #{i+1}", remaining_tables, key=f"right_table_{i}")
                right_columns = [col[0] for col in table_columns.get(right_table, [])]
                right_column = st.selectbox(f"Right Column #{i+1}", right_columns, key=f"right_column_{i}")
            
            join_conditions.append({
                'left_table': left_table,
                'left_column': left_column,
                'join_type': join_type,
                'right_table': right_table,
                'right_column': right_column
            })
    
    # Aggregation options
    st.subheader("Aggregations and Group By")
    
    aggregations = {}
    for col in selected_columns:
        col1, col2 = st.columns(2)
        with col1:
            st.write(col)
        with col2:
            agg_options = ["None", "SUM", "AVG", "MIN", "MAX", "COUNT"]
            agg_choice = st.selectbox(f"Aggregation for {col}", agg_options, key=f"agg_{col}")
            if agg_choice != "None":
                aggregations[col] = agg_choice
    
    # Group by columns
    if aggregations:
        non_agg_columns = [col for col in selected_columns if col not in aggregations]
        group_by_columns = st.multiselect("Group By Columns", non_agg_columns)
    else:
        group_by_columns = []
    
    # Generate SQL preview
    if selected_columns:
        template_data = {
            'selected_tables': selected_tables,
            'selected_columns': selected_columns,
            'join_conditions': join_conditions,
            'aggregations': aggregations,
            'group_by_columns': group_by_columns
        }
        
        sql_query = generate_sql_from_template(json.dumps(template_data))
        
        st.subheader("SQL Preview")
        st.code(sql_query, language="sql")
        
        # Save template button
        if st.button("Save Template"):
            if not template_name:
                st.error("Please provide a template name")
            else:
                success = save_template(
                    template_name=template_name,
                    template_type="PARENT",
                    parent_template_id=None,
                    sql_query=sql_query,
                    template_data=json.dumps(template_data)
                )
                
                if success:
                    st.success(f"Template '{template_name}' saved successfully!")
                    st.session_state['templates'] = get_templates()
    
        # Execute query button
        if st.button("Execute Query"):
            df = execute_query(sql_query)
            if df is not None:
                st.subheader("Query Results")
                st.dataframe(df)

def child_template_creation():
    st.subheader("Create Child SQL Template")
    
    # Get parent templates
    parent_templates = [t for t in st.session_state.get('templates', []) if t[2] == "PARENT"]
    
    if not parent_templates:
        st.warning("No parent templates available. Please create a parent template first.")
        return
    
    template_name = st.text_input("Child Template Name")
    
    # Select parent template
    parent_template_options = [(t[0], t[1]) for t in parent_templates]
    parent_selection = st.selectbox(
        "Select Parent Template", 
        parent_template_options, 
        format_func=lambda x: x[1]
    )
    
    parent_id = parent_selection[0]
    
    # Get parent template details
    parent_details = get_template_details(parent_id)
    
    if not parent_details:
        st.error("Failed to load parent template details")
        return
    
    # Execute parent query to get columns
    parent_sql = parent_details['sql_query']
    
    st.subheader("Parent SQL")
    st.code(parent_sql, language="sql")
    
    # Execute parent query to get a dataframe of results
    df = execute_query(parent_sql)
    
    if df is None:
        st.error("Failed to execute parent query")
        return
    
    st.subheader("Parent Query Results")
    st.dataframe(df.head())
    
    # Get columns from parent query
    parent_columns = df.columns.tolist()
    
    # Select columns from parent query
    selected_columns = st.multiselect("Select Columns from Parent Query", parent_columns)
    
    # Aggregation options
    aggregations = {}
    
    if selected_columns:
        st.subheader("Aggregations and Group By")
        
        for col in selected_columns:
            col1, col2 = st.columns(2)
            with col1:
                st.write(col)
            with col2:
                agg_options = ["None", "SUM", "AVG", "MIN", "MAX", "COUNT"]
                agg_choice = st.selectbox(f"Aggregation for {col}", agg_options, key=f"child_agg_{col}")
                if agg_choice != "None":
                    aggregations[col] = agg_choice
    
    # Group by columns
    if aggregations:
        non_agg_columns = [col for col in selected_columns if col not in aggregations]
        group_by_columns = st.multiselect("Group By Columns", non_agg_columns)
    else:
        group_by_columns = []
    
    # Generate SQL for child template
    if selected_columns:
        # Create subquery from parent
        subquery = f"(\n{parent_sql}\n) parent_query"
        
        # Build the SELECT part
        select_parts = []
        for col in selected_columns:
            if col in aggregations and aggregations[col]:
                agg_type = aggregations[col]
                select_parts.append(f"{agg_type}(parent_query.{col}) AS {col}_{agg_type.lower()}")
            else:
                select_parts.append(f"parent_query.{col}")
        
        select_clause = ",\n    ".join(select_parts)
        
        # Build the GROUP BY part
        group_by_clause = ""
        if group_by_columns:
            group_by_clause = "\nGROUP BY " + ",\n    ".join([f"parent_query.{col}" for col in group_by_columns])
        
        # Combine all parts
        sql_query = f"SELECT\n    {select_clause}\nFROM {subquery}{group_by_clause}"
        
        template_data = {
            'parent_template_id': parent_id,
            'selected_columns': selected_columns,
            'aggregations': aggregations,
            'group_by_columns': group_by_columns
        }
        
        st.subheader("Child SQL Preview")
        st.code(sql_query, language="sql")
        
        # Save template button
        if st.button("Save Child Template"):
            if not template_name:
                st.error("Please provide a template name")
            else:
                success = save_template(
                    template_name=template_name,
                    template_type="CHILD",
                    parent_template_id=parent_id,
                    sql_query=sql_query,
                    template_data=json.dumps(template_data)
                )
                
                if success:
                    st.success(f"Child template '{template_name}' saved successfully!")
                    st.session_state['templates'] = get_templates()
        
        # Execute query button
        if st.button("Execute Child Query"):
            df = execute_query(sql_query)
            if df is not None:
                st.subheader("Child Query Results")
                st.dataframe(df)

def edit_template():
    st.subheader("Edit SQL Template")
    
    # Get templates
    templates = st.session_state.get('templates', [])
    
    if not templates:
        st.warning("No templates available to edit.")
        return
    
    # Select template to edit
    template_options = [(t[0], t[1], t[2]) for t in templates]
    template_selection = st.selectbox(
        "Select Template to Edit", 
        template_options, 
        format_func=lambda x: f"{x[1]} ({x[2]})"
    )
    
    template_id = template_selection[0]
    template_type = template_selection[2]
    
    # Get template details
    template_details = get_template_details(template_id)
    
    if not template_details:
        st.error("Failed to load template details")
        return
    
    template_name = st.text_input("Template Name", value=template_details['template_name'])
    
    template_data = json.loads(template_details['template_data'])
    
    if template_type == "PARENT":
        edit_parent_template(template_id, template_name, template_data)
    else:  # CHILD
        edit_child_template(template_id, template_name, template_data)

def edit_parent_template(template_id, template_name, template_data):
    tables = get_all_tables()
    
    # Get previously selected values
    prev_selected_tables = template_data.get('selected_tables', [])
    prev_selected_columns = template_data.get('selected_columns', [])
    prev_join_conditions = template_data.get('join_conditions', [])
    prev_aggregations = template_data.get('aggregations', {})
    prev_group_by_columns = template_data.get('group_by_columns', [])
    
    # Select tables
    selected_tables = st.multiselect("Select Tables", tables, default=prev_selected_tables)
    
    # Store selected tables
    if selected_tables:
        st.session_state['selected_tables'] = selected_tables
    else:
        st.session_state['selected_tables'] = prev_selected_tables
    
    # Get columns for each selected table
    all_columns = []
    table_columns = {}
    
    for table in st.session_state['selected_tables']:
        columns = get_table_columns(table)
        table_columns[table] = columns
        all_columns.extend([f"{table}.{col[0]}" for col in columns])
    
    # Select columns
    selected_columns = st.multiselect("Select Columns", all_columns, default=prev_selected_columns)
    
    # Set up join conditions if multiple tables are selected
    join_conditions = []
    
    if len(st.session_state['selected_tables']) > 1:
        st.subheader("Join Conditions")
        
        # Pre-fill with existing join conditions
        num_joins = len(prev_join_conditions) if prev_join_conditions else len(st.session_state['selected_tables']) - 1
        
        for i in range(num_joins):
            col1, col2, col3 = st.columns(3)
            
            prev_join = prev_join_conditions[i] if i < len(prev_join_conditions) else {}
            
            with col1:
                left_table = st.selectbox(
                    f"Left Table #{i+1}", 
                    st.session_state['selected_tables'], 
                    index=st.session_state['selected_tables'].index(prev_join.get('left_table', st.session_state['selected_tables'][0])) if prev_join.get('left_table') in st.session_state['selected_tables'] else 0,
                    key=f"edit_left_table_{i}"
                )
                
                left_columns = [col[0] for col in table_columns.get(left_table, [])]
                left_column_default = prev_join.get('left_column', '')
                left_column_index = left_columns.index(left_column_default) if left_column_default in left_columns else 0
                
                left_column = st.selectbox(
                    f"Left Column #{i+1}", 
                    left_columns,
                    index=left_column_index if left_columns else 0,
                    key=f"edit_left_column_{i}"
                )
            
            with col2:
                join_types = ["INNER JOIN", "LEFT OUTER JOIN", "RIGHT OUTER JOIN", "FULL OUTER JOIN"]
                join_type_default = prev_join.get('join_type', 'INNER JOIN')
                join_type_index = join_types.index(join_type_default) if join_type_default in join_types else 0
                
                join_type = st.selectbox(
                    f"Join Type #{i+1}", 
                    join_types,
                    index=join_type_index,
                    key=f"edit_join_type_{i}"
                )
            
            with col3:
                remaining_tables = [t for t in st.session_state['selected_tables'] if t != left_table]
                right_table_default = prev_join.get('right_table', '')
                right_table_index = remaining_tables.index(right_table_default) if right_table_default in remaining_tables else 0
                
                right_table = st.selectbox(
                    f"Right Table #{i+1}", 
                    remaining_tables,
                    index=right_table_index if remaining_tables else 0,
                    key=f"edit_right_table_{i}"
                )
                
                right_columns = [col[0] for col in table_columns.get(right_table, [])]
                right_column_default = prev_join.get('right_column', '')
                right_column_index = right_columns.index(right_column_default) if right_column_default in right_columns else 0
                
                right_column = st.selectbox(
                    f"Right Column #{i+1}", 
                    right_columns,
                    index=right_column_index if right_columns else 0,
                    key=f"edit_right_column_{i}"
                )
            
            join_conditions.append({
                'left_table': left_table,
                'left_column': left_column,
                'join_type': join_type,
                'right_table': right_table,
                'right_column': right_column
            })
    
    # Aggregation options
    st.subheader("Aggregations and Group By")
    
    aggregations = {}
    for col in selected_columns:
        col1, col2 = st.columns(2)
        with col1:
            st.write(col)
        with col2:
            agg_options = ["None", "SUM", "AVG", "MIN", "MAX", "COUNT"]
            prev_agg = prev_aggregations.get(col, "None")
            agg_index = agg_options.index(prev_agg) if prev_agg in agg_options else 0
            
            agg_choice = st.selectbox(
                f"Aggregation for {col}", 
                agg_options, 
                index=agg_index,
                key=f"edit_agg_{col}"
            )
            
            if agg_choice != "None":
                aggregations[col] = agg_choice
    
    # Group by columns
    if aggregations:
        non_agg_columns = [col for col in selected_columns if col not in aggregations]
        group_by_columns = st.multiselect(
            "Group By Columns", 
            non_agg_columns, 
            default=[col for col in prev_group_by_columns if col in non_agg_columns]
        )
    else:
        group_by_columns = []
    
    # Generate SQL preview
    if selected_columns:
        updated_template_data = {
            'selected_tables': selected_tables,
            'selected_columns': selected_columns,
            'join_conditions': join_conditions,
            'aggregations': aggregations,
            'group_by_columns': group_by_columns
        }
        
        sql_query = generate_sql_from_template(json.dumps(updated_template_data))
        
        st.subheader("SQL Preview")
        st.code(sql_query, language="sql")
        
        # Update template button
        if st.button("Update Template"):
            if not template_name:
                st.error("Please provide a template name")
            else:
                success = update_template(
                    template_id=template_id,
                    template_name=template_name,
                    sql_query=sql_query,
                    template_data=json.dumps(updated_template_data)
                )
                
                if success:
                    st.success(f"Template '{template_name}' updated successfully!")
                    st.session_state['templates'] = get_templates()
        
        # Execute query button
        if st.button("Execute Query"):
            df = execute_query(sql_query)
            if df is not None:
                st.subheader("Query Results")
                st.dataframe(df)

def edit_child_template(template_id, template_name, template_data):
    # Get parent template ID
    parent_id = template_data.get('parent_template_id')
    
    if not parent_id:
        st.error("Invalid child template: No parent template found")
        return
    
    # Get parent template details
    parent_details = get_template_details(parent_id)
    
    if not parent_details:
        st.error("Failed to load parent template details")
        return
    
    st.write(f"Parent Template: {parent_details['template_name']}")
    
    # Execute parent query to get columns
    parent_sql = parent_details['sql_query']
    
    st.subheader("Parent SQL")
    st.code(parent_sql, language="sql")
    
    # Execute parent query to get a dataframe of results
    df = execute_query(parent_sql)
    
    if df is None:
        st.error("Failed to execute parent query")
        return
    
    # Get columns from parent query
    parent_columns = df.columns.tolist()
    
    # Get previously selected values
    prev_selected_columns = template_data.get('selected_columns', [])
    prev_aggregations = template_data.get('aggregations', {})
    prev_group_by_columns = template_data.get('group_by_columns', [])
    
    # Select columns from parent query
    selected_columns = st.multiselect(
        "Select Columns from Parent Query", 
        parent_columns, 
        default=[col for col in prev_selected_columns if col in parent_columns]
    )
    
    # Aggregation options
    aggregations = {}
    
    if selected_columns:
        st.subheader("Aggregations and Group By")
        
        for col in selected_columns:
            col1, col2 = st.columns(2)
            with col1:
                st.write(col)
            with col2:
                agg_options = ["None", "SUM", "AVG", "MIN", "MAX", "COUNT"]
                prev_agg = prev_aggregations.get(col, "None")
                agg_index = agg_options.index(prev_agg) if prev_agg in agg_options else 0
                
                agg_choice = st.selectbox(
                    f"Aggregation for {col}", 
                    agg_options, 
                    index=agg_index,
                    key=f"edit_child_agg_{col}"
                )
                
                if agg_choice != "None":
                    aggregations[col] = agg_choice
    
    # Group by columns
    if aggregations:
        non_agg_columns = [col for col in selected_columns if col not in aggregations]
        group_by_columns = st.multiselect(
            "Group By Columns", 
            non_agg_columns, 
            default=[col for col in prev_group_by_columns if col in non_agg_columns]
        )
    else:
        group_by_columns = []
    
    # Generate SQL for child template
    if selected_columns:
        # Create subquery from parent
        subquery = f"(\n{parent_sql}\n) parent_query"
        
        # Build the SELECT part
        select_parts = []
        for col in selected_columns:
            if col in aggregations and aggregations[col]:
                agg_type = aggregations[col]
                select_parts.append(f"{agg_type}(parent_query.{col}) AS {col}_{agg_type.lower()}")
            else:
                select_parts.append(f"parent_query.{col}")
        
        select_clause = ",\n    ".join(select_parts)
        
        # Build the GROUP BY part
        group_by_clause = ""
        if group_by_columns:
            group_by_clause = "\nGROUP BY " + ",\n    ".join([f"parent_query.{col}" for col in group_by_columns])
        
        # Combine all parts
        sql_query = f"SELECT\n    {select_clause}\nFROM {subquery}{group_by_clause}"
        
        updated_template_data = {
            'parent_template_id': parent_id,
            'selected_columns': selected_columns,
            'aggregations': aggregations,
            'group_by_columns': group_by_columns
        }
        
        st.subheader("Child SQL Preview")
        st.code(sql_query, language="sql")
        
        # Update template button
        if st.button("Update Child Template"):
            if not template_name:
                st.error("Please provide a template name")
            else:
                success = update_template(
                    template_id=template_id,
                    template_name=template_name,
                    sql_query=sql_query,
                    template_data=json.dumps(updated_template_data)
                )
                
                if success:
                    st.success(f"Child template '{template_name}' updated successfully!")
                    st.session_state['templates'] = get_templates()
        
        # Execute query button
        if st.button("Execute Child Query"):
            df = execute_query(sql_query)
            if df is not None:
                st.subheader("Child Query Results")
                st.dataframe(df)

def view_template():
    st.subheader("View SQL Template")
    
    # Get templates
    templates = st.session_state.get('templates', [])
    
    if not templates:
        st.warning("No templates available to view.")
        return
    
    # Select template to view
    template_options = [(t[0], t[1], t[2]) for t in templates]
    template_selection = st.selectbox(
        "Select Template to View", 
        template_options, 
        format_func=lambda x: f"{x[1]} ({x[2]})"
    )
    
    template_id = template_selection[0]
    
    # Get template details
    template_details = get_template_details(template_id)
    
    if not template_details:
        st.error("Failed to load template details")
        return
    
    st.write(f"Template Type: {template_details['template_type']}")
    
    if template_details['parent_template_id']:
        parent_details = get_template_details(template_details['parent_template_id'])
        if parent_details:
            st.write(f"Parent Template: {parent_details['template_name']}")
    
    st.subheader("SQL Query")
    st.code(template_details['sql_query'], language="sql")
    
    # Execute query button
    if st.button("Execute Query"):
        df = execute_query(template_details['sql_query'])
        if df is not None:
            st.subheader("Query Results")
            st.dataframe(df)

def main():
    st.title("SQL Template Manager")
    
    # Initialize session state
    if 'connected' not in st.session_state:
        st.session_state['connected'] = False
    
    if 'templates' not in st.session_state:
        st.session_state['templates'] = []
    
    # Login/Connection form
    if not st.session_state['connected']:
        login_form()
    else:
        # Refresh templates list
        st.session_state['templates'] = get_templates()
        
        # Create navigation
        st.sidebar.title("Navigation")
        page = st.sidebar.radio(
            "Go to", 
            ["Create Parent Template", "Create Child Template", "Edit Template", "View Template"]
        )
        
        # Display the selected page
        if page == "Create Parent Template":
            parent_template_creation()
        elif page == "Create Child Template":
            child_template_creation()
        elif page == "Edit Template":
            edit_template()
        elif page == "View Template":
            view_template()
        
        # Logout button
        if st.sidebar.button("Disconnect"):
            st.session_state['connected'] = False
            st.session_state['conn_info'] = {}
            st.session_state['templates'] = []
            st.experimental_rerun()

if __name__ == "__main__":
    main()
